# -*- coding: utf-8 -*-
"""
任务业务逻辑
"""

from typing import List, Dict, Optional, Any, AsyncGenerator
import asyncio
import json
import random
import uuid
from datetime import datetime, timedelta
from pathlib import Path

import aiofiles

from app.config.setting import settings
from app.core.database import AsyncSessionLocal
from app.core.exceptions import CustomException
from app.core.logger import logger
from app.api.v1.module_system.auth.schema import AuthSchema
from app.api.v1.module_system.params.crud import ParamsCRUD

from ..service_module.crud import ServiceCRUD
from ..server.crud import ServerCRUD
from .crud import TaskCRUD
from .schema import TaskOutSchema, TaskDetailSchema, TaskLogSchema


class TaskService:
    """任务管理服务层"""

    LOG_DIR = settings.BASE_DIR.joinpath("logs", "operations_task")
    LOG_CONFIG_KEY = "operations_task_log_keep_days"

    @classmethod
    def _ensure_log_dir(cls) -> None:
        cls.LOG_DIR.mkdir(parents=True, exist_ok=True)

    @classmethod
    def _build_log_path(cls, task_type: str, node_ip: str) -> Path:
        cls._ensure_log_dir()
        safe_ip = node_ip.replace(":", "-").replace(".", "-")
        filename = f"{task_type}_{safe_ip}_{datetime.now().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:8]}.log"
        return cls.LOG_DIR.joinpath(filename)

    @classmethod
    def _build_task_params(cls, auth: AuthSchema, node: Any, task_type: str) -> Dict[str, Any]:
        user = auth.user
        operator_name = None
        if user:
            operator_name = getattr(user, "name", None) or getattr(user, "nickname", None) or user.username
        return {
            "task_type": task_type,
            "operator_id": user.id if user else None,
            "operator_name": operator_name,
            "trigger_time": datetime.utcnow().isoformat(),
            "node": {
                "id": node.id,
                "ip": node.ip,
                "port": node.port,
                "service_id": node.service_id,
            },
        }

    @classmethod
    async def _write_log(cls, log_path: Path, message: str) -> None:
        cls._ensure_log_dir()
        async with aiofiles.open(log_path, "a", encoding="utf-8") as log_file:
            await log_file.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {message}\n")

    @classmethod
    async def _cleanup_expired_logs(cls, auth: AuthSchema) -> None:
        try:
            config = await ParamsCRUD(auth).get_obj_by_key_crud(key=cls.LOG_CONFIG_KEY)
            if config and config.config_value:
                days_to_keep = int(config.config_value)
            else:
                days_to_keep = settings.LOG_RETENTION_DAYS
        except Exception as exc:
            logger.warning(f"读取日志保留配置失败，使用默认值: {exc}")
            days_to_keep = settings.LOG_RETENTION_DAYS

        if days_to_keep <= 0:
            return

        cutoff = datetime.now() - timedelta(days=days_to_keep)
        cls._ensure_log_dir()
        for log_file in cls.LOG_DIR.glob("*.log"):
            try:
                if datetime.fromtimestamp(log_file.stat().st_mtime) < cutoff:
                    log_file.unlink(missing_ok=True)
            except FileNotFoundError:
                continue
            except Exception as exc:
                logger.error(f"清理日志文件失败 {log_file}: {exc}")

    @classmethod
    async def _simulate_task(
        cls,
        *,
        base_auth: AuthSchema,
        task_id: int,
        log_path: Path,
        task_type: str,
    ) -> None:
        steps = [
            "任务初始化",
            "校验节点状态",
            "准备执行环境",
            "拉取最新版本",
            "执行构建流程",
            "同步资源文件",
            "重启相关服务" if task_type == "deploy" else "执行服务重启",
            "健康检查",
        ]
        failure_rate = 0.2 if task_type == "deploy" else 0.15

        async with AsyncSessionLocal() as new_db:
            new_auth = AuthSchema(db=new_db, user=base_auth.user, check_data_scope=False)
            new_task_crud = TaskCRUD(new_auth)

            try:
                await cls._write_log(log_path, f"开始执行{'部署' if task_type == 'deploy' else '重启'}任务")
                total_steps = len(steps)
                for index, step in enumerate(steps, start=1):
                    await asyncio.sleep(random.uniform(0.6, 1.2))
                    await cls._write_log(log_path, step)
                    progress = min(int(index / (total_steps + 1) * 100), 95)
                    await new_task_crud.update(id=task_id, data={"progress": progress})
                    await new_db.commit()

                await asyncio.sleep(random.uniform(0.8, 1.5))
                success = random.random() > failure_rate
                if success:
                    await cls._write_log(log_path, "任务执行成功")
                    update_data = {"task_status": "success", "progress": 100, "error_message": None}
                else:
                    await cls._write_log(log_path, "任务执行失败")
                    update_data = {
                        "task_status": "failed",
                        "progress": 100,
                        "error_message": "模拟执行失败，请检查日志",
                    }
                await new_task_crud.update(id=task_id, data=update_data)
                await new_db.commit()
            except asyncio.CancelledError:
                await new_db.rollback()
                await cls._write_log(log_path, "任务被取消")
                await new_task_crud.update(
                    id=task_id,
                    data={"task_status": "failed", "error_message": "任务被取消", "progress": 100},
                )
                await new_db.commit()
                raise
            except Exception as exc:
                await new_db.rollback()
                logger.error(f"模拟任务执行失败 {task_id}: {exc}")
                await cls._write_log(log_path, f"任务执行异常: {exc}")
                await new_task_crud.update(
                    id=task_id,
                    data={
                        "task_status": "failed",
                        "error_message": f"执行异常: {exc}",
                        "progress": 100,
                    },
                )
                await new_db.commit()
            finally:
                await cls._cleanup_expired_logs(new_auth)

    @classmethod
    async def _create_tasks(
        cls,
        auth: AuthSchema,
        nodes: List[Any],
        task_type: str,
    ) -> List[Dict[str, Any]]:
        task_crud = TaskCRUD(auth)
        task_records: List[Dict[str, Any]] = []

        for node in nodes:
            log_path = cls._build_log_path(task_type=task_type, node_ip=node.ip)
            params_dict = cls._build_task_params(auth=auth, node=node, task_type=task_type)
            task_data = {
                "service_id": node.service_id,
                "node_id": node.id,
                "ip": node.ip,
                "task_type": task_type,
                "task_status": "running",
                "progress": 0,
                "log_path": str(log_path),
                "params": json.dumps(params_dict, ensure_ascii=False),
            }
            task = await task_crud.create(data=task_data)
            await cls._write_log(log_path, "任务创建成功，等待执行")
            task_records.append({"task": task, "log_path": log_path})

        await auth.db.commit()
        return task_records

    @classmethod
    async def get_recent_tasks_service(cls, auth: AuthSchema, limit: int = 20) -> List[Dict]:
        tasks = await TaskCRUD(auth).get_recent_tasks_crud(limit=limit, preload=["node", "service"])
        return [TaskOutSchema.model_validate(task).model_dump() for task in tasks]

    @classmethod
    async def get_task_page_service(
        cls,
        auth: AuthSchema,
        page_no: int,
        page_size: int,
        search,
        order_by,
    ) -> Dict:
        page_no = page_no or 1
        page_size = page_size or 10
        offset = (page_no - 1) * page_size
        search_dict = search.__dict__ if hasattr(search, "__dict__") else search
        order = order_by or [{"created_at": "desc"}]
        return await TaskCRUD(auth).page_crud(
            offset=offset,
            limit=page_size,
            order_by=order,
            search=search_dict,
            out_schema=TaskOutSchema,
            preload=["service", "node"],
        )

    @classmethod
    async def get_task_detail_service(cls, auth: AuthSchema, task_id: int) -> Dict:
        task = await TaskCRUD(auth).get_by_id_crud(
            id=task_id,
            preload=["node", "node.service", "service"],
        )
        if not task:
            raise CustomException(msg="任务不存在")
        data = TaskDetailSchema.model_validate(task).model_dump()
        log_path = task.log_path
        if log_path:
            path = Path(log_path)
            if path.exists():
                data["log_size"] = path.stat().st_size
        return data

    @classmethod
    async def get_task_log_service(cls, auth: AuthSchema, task_id: int) -> Dict:
        task = await TaskCRUD(auth).get_by_id_crud(id=task_id)
        if not task:
            raise CustomException(msg="任务不存在")
        if not task.log_path:
            raise CustomException(msg="任务未生成日志")
        log_path = Path(task.log_path)
        if not log_path.exists():
            raise CustomException(msg="日志文件不存在或已清理")
        async with aiofiles.open(log_path, "r", encoding="utf-8") as log_file:
            content = await log_file.read()
        return TaskLogSchema(content=content).model_dump()

    @classmethod
    async def delete_task_service(cls, auth: AuthSchema, ids: List[int]) -> None:
        if len(ids) < 1:
            raise CustomException(msg="删除对象不能为空")

        tasks_to_delete = []
        for task_id in ids:
            task = await TaskCRUD(auth).get_by_id_crud(id=task_id)
            if not task:
                raise CustomException(msg=f"任务 {task_id} 不存在")
            if task.task_status == "running":
                raise CustomException(msg=f"任务 {task_id} 正在执行，无法删除")
            tasks_to_delete.append(task)

        await TaskCRUD(auth).delete_crud(ids=ids)
        await auth.db.commit()

        for task in tasks_to_delete:
            if task.log_path:
                path = Path(task.log_path)
                try:
                    path.unlink(missing_ok=True)
                except Exception as exc:
                    logger.warning(f"删除任务日志失败 {path}: {exc}")

    @classmethod
    async def deploy_service(cls, auth: AuthSchema, node_ids: List[int]) -> Dict:
        if not node_ids:
            raise CustomException(msg="请选择需要部署的节点")

        nodes = []
        for node_id in node_ids:
            node = await ServerCRUD(auth).get_by_id_crud(id=node_id)
            if not node:
                raise CustomException(msg=f"节点ID {node_id} 不存在")
            nodes.append(node)

        task_records = await cls._create_tasks(auth=auth, nodes=nodes, task_type="deploy")

        for record in task_records:
            task = record["task"]
            log_path = Path(record["log_path"])
            asyncio.create_task(
                cls._simulate_task(
                    base_auth=auth,
                    task_id=task.id,
                    log_path=log_path,
                    task_type="deploy",
                )
            )

        return {
            "message": "部署任务已启动",
            "task_ids": [record["task"].id for record in task_records],
            "task_count": len(task_records),
        }

    @classmethod
    async def restart_service(cls, auth: AuthSchema, node_ids: List[int]) -> Dict:
        if not node_ids:
            raise CustomException(msg="请选择需要重启的节点")

        nodes = []
        for node_id in node_ids:
            node = await ServerCRUD(auth).get_by_id_crud(id=node_id)
            if not node:
                raise CustomException(msg=f"节点ID {node_id} 不存在")
            nodes.append(node)

        task_records = await cls._create_tasks(auth=auth, nodes=nodes, task_type="restart")

        for record in task_records:
            task = record["task"]
            log_path = Path(record["log_path"])
            asyncio.create_task(
                cls._simulate_task(
                    base_auth=auth,
                    task_id=task.id,
                    log_path=log_path,
                    task_type="restart",
                )
            )

        return {
            "message": "重启任务已启动",
            "task_ids": [record["task"].id for record in task_records],
            "task_count": len(task_records),
        }

    @classmethod
    def _format_sse(cls, event: str, data: str) -> str:
        return f"event: {event}\ndata: {data}\n\n"

    @classmethod
    async def stream_task_log_service(cls, auth: AuthSchema, task_id: int) -> AsyncGenerator[str, None]:
        task = await TaskCRUD(auth).get_by_id_crud(id=task_id)
        if not task or not task.log_path:
            async def error_stream() -> AsyncGenerator[str, None]:
                yield cls._format_sse("error", "任务不存在或未生成日志")
            return error_stream()

        log_path = Path(task.log_path)

        async def event_stream() -> AsyncGenerator[str, None]:
            file = None
            position = 0
            try:
                if log_path.exists():
                    file = open(log_path, "r", encoding="utf-8")
                    for line in file:
                        yield cls._format_sse("log", line.rstrip("\n"))
                    position = file.tell()
                else:
                    yield cls._format_sse("info", "日志文件尚未生成")

                inactive_cycles = 0
                while True:
                    if log_path.exists():
                        if file is None or file.closed:
                            file = open(log_path, "r", encoding="utf-8")
                            file.seek(position)
                        line = file.readline()
                        if line:
                            position = file.tell()
                            inactive_cycles = 0
                            yield cls._format_sse("log", line.rstrip("\n"))
                            continue
                    inactive_cycles += 1
                    await asyncio.sleep(1)

                    async with AsyncSessionLocal() as new_db:
                        new_auth = AuthSchema(db=new_db, user=auth.user, check_data_scope=False)
                        fresh_task = await TaskCRUD(new_auth).get_by_id_crud(id=task_id)

                    if not fresh_task:
                        yield cls._format_sse("error", "任务已删除")
                        break

                    if fresh_task.task_status in ("success", "failed"):
                        if log_path.exists():
                            if position >= log_path.stat().st_size:
                                status_text = "完成" if fresh_task.task_status == "success" else "失败"
                                yield cls._format_sse("end", f"任务已{status_text}")
                                break
                        else:
                            yield cls._format_sse("end", "任务已结束，日志不存在")
                            break

                    if inactive_cycles > 60:
                        yield cls._format_sse("end", "长时间无新日志，结束推送")
                        break
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.error(f"推送任务日志失败: {exc}")
                yield cls._format_sse("error", f"日志推送异常: {exc}")
            finally:
                if file and not file.closed:
                    file.close()

        return event_stream()

