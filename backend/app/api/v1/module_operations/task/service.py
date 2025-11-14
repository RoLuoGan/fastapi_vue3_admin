# -*- coding: utf-8 -*-
"""
任务业务逻辑
只负责业务层拼装和调度，委托具体逻辑给其他组件
"""

from typing import List, Dict, Optional, Any, AsyncGenerator
import asyncio
import json
from datetime import datetime
from pathlib import Path

import aiofiles

from app.core.exceptions import CustomException
from app.core.logger import logger
from app.api.v1.module_system.auth.schema import AuthSchema

from ..service_module.crud import ServiceCRUD
from ..server.crud import ServerCRUD
from .crud import TaskCRUD
from .schema import TaskOutSchema, TaskDetailSchema, TaskLogSchema
from .executor import TaskExecutor
from .streamer import TaskLogStreamer


class TaskService:
    """任务管理服务层 - 只负责业务拼装和调度"""

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
    async def _create_tasks(
        cls,
        auth: AuthSchema,
        nodes: List[Any],
        task_type: str,
    ) -> List[Dict[str, Any]]:
        """
        创建任务记录
        委托日志路径构建给 TaskExecutor，委托日志写入给 TaskExecutor
        """
        task_crud = TaskCRUD(auth)
        task_records: List[Dict[str, Any]] = []

        for node in nodes:
            # 委托给 TaskExecutor 构建日志路径
            log_path = TaskExecutor.build_log_path(task_type=task_type, node_ip=node.ip)
            
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
            
            # 委托给 TaskExecutor 写入初始日志
            await TaskExecutor.write_log(log_path, "任务创建成功，等待执行")
            
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
            # 使用 TaskExecutor 执行任务
            asyncio.create_task(
                TaskExecutor.execute_task(
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
            # 使用 TaskExecutor 执行任务
            asyncio.create_task(
                TaskExecutor.execute_task(
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
    async def stream_task_log_service(
        cls,
        auth: AuthSchema,
        task_id: int,
        last_event_id: Optional[str] = None,
    ) -> AsyncGenerator[str, None]:
        """
        任务日志流服务
        委托给 TaskLogStreamer 处理
        
        返回 AsyncGenerator，可以在 controller 中 await 获取生成器
        """
        # 返回生成器，这里可以做一些初始化工作
        return TaskLogStreamer.stream_task_log(
            auth=auth,
            task_id=task_id,
            last_event_id=last_event_id,
        )

