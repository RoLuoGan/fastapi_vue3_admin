# -*- coding: utf-8 -*-
"""
任务执行器
负责任务的实际执行逻辑和日志写入
"""

import asyncio
import uuid
import sys
from importlib import import_module
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Any, Dict, Tuple

import aiofiles

from app.config.setting import settings
from app.core.database import AsyncSessionLocal
from app.core.logger import logger
from app.api.v1.module_system.auth.schema import AuthSchema
from .crud import TaskCRUD


class TaskExecutor:
    """任务执行器，负责任务的实际执行逻辑和日志写入"""

    LOG_DIR = settings.BASE_DIR.joinpath("logs", "operations_task")
    LOG_CONFIG_KEY = "operations_task_log_keep_days"

    @classmethod
    def ensure_log_dir(cls) -> None:
        """确保日志目录存在"""
        cls.LOG_DIR.mkdir(parents=True, exist_ok=True)

    @classmethod
    def build_log_path(cls, task_type: str, node_ip: str) -> Path:
        """构建日志文件路径"""
        cls.ensure_log_dir()
        safe_ip = node_ip.replace(":", "-").replace(".", "-")
        filename = f"{task_type}_{safe_ip}_{datetime.now().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:8]}.log"
        return cls.LOG_DIR.joinpath(filename)

    @classmethod
    async def write_log(cls, log_path: Path, message: str) -> None:
        """
        写入日志到文件
        
        Args:
            log_path: 日志文件路径
            message: 日志消息
        """
        cls.ensure_log_dir()
        async with aiofiles.open(log_path, "a", encoding="utf-8") as log_file:
            await log_file.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {message}\n")

    @classmethod
    def _build_operator_metas_for_script(cls, operator_metas: List[dict]) -> List[Dict]:
        """
        构建传递给脚本的 operator_metas 格式
        
        Args:
            operator_metas: 操作元数据列表，格式: [{"service_id": 1, "nodes": [node_obj, ...]}, ...]
        
        Returns:
            List[Dict]: 格式化的操作元数据列表
        """
        result = []
        for meta in operator_metas:
            service_id = meta.get("service_id")
            service_nodes = meta.get("nodes", [])
            
            # 获取服务名称
            service_name = None
            if service_nodes:
                first_node = service_nodes[0]
                if hasattr(first_node, 'services'):
                    for svc in (first_node.services or []):
                        if svc.id == service_id:
                            service_name = svc.name
                            break
                if not service_name and hasattr(first_node, 'service'):
                    if first_node.service and first_node.service.id == service_id:
                        service_name = first_node.service.name
            
            # 构建节点列表
            node_list = []
            for node in service_nodes:
                node_dict = {
                    "id": node.id,
                    "ip": node.ip,
                    "port": node.port or 22,
                    "service_id": service_id,
                }
                node_list.append(node_dict)
            
            result.append({
                "service_id": service_id,
                "service_name": service_name,
                "nodes": node_list,
            })
        
        return result

    @classmethod
    async def execute_batch_task(
        cls,
        *,
        base_auth: AuthSchema,
        task_id: int,
        log_path: Path,
        nodes: List[Any],
        task_type: str,
        operator_metas: Optional[List[dict]] = None,
    ) -> None:
        """
        执行批次任务（多个节点）- 通过 import_module 调用脚本逻辑
        
        Args:
            base_auth: 基础认证信息
            task_id: 任务ID
            log_path: 日志文件路径
            nodes: 节点列表
            task_type: 任务类型 (deploy/restart)
            operator_metas: 操作元数据（可选），格式: [{"service_id": 1, "nodes": [node_obj, ...]}, ...]
        """
        async with AsyncSessionLocal() as new_db:
            new_auth = AuthSchema(db=new_db, user=base_auth.user, check_data_scope=False)
            new_task_crud = TaskCRUD(new_auth)
            
            try:
                # 构建脚本参数（脚本位于 env 同级的 scripts 目录）
                script_path = settings.BASE_DIR.joinpath("scripts", "execute_batch_task.py")
                if not script_path.exists():
                    raise FileNotFoundError(f"脚本文件不存在: {script_path}")
                
                # 构建 operator_metas（如果提供）
                script_operator_metas = None
                if operator_metas:
                    script_operator_metas = cls._build_operator_metas_for_script(operator_metas)
                else:
                    # 如果没有提供 operator_metas，从 nodes 构建
                    # 按 service_id 分组
                    nodes_by_service = {}
                    for node in nodes:
                        service_id = node.service_id or 0
                        if service_id not in nodes_by_service:
                            nodes_by_service[service_id] = []
                        nodes_by_service[service_id].append(node)
                    
                    script_operator_metas = []
                    for service_id, service_nodes in nodes_by_service.items():
                        service_name = None
                        if service_nodes:
                            first_node = service_nodes[0]
                            if hasattr(first_node, 'service') and first_node.service:
                                service_name = first_node.service.name
                        
                        node_list = []
                        for node in service_nodes:
                            node_list.append({
                                "id": node.id,
                                "ip": node.ip,
                                "port": node.port or 22,
                                "service_id": service_id,
                            })
                        
                        script_operator_metas.append({
                            "service_id": service_id,
                            "service_name": service_name,
                            "nodes": node_list,
                        })
                
                logger.info(f"导入批次任务脚本模块: {script_path}")
                
                # 通过 import_module 导入脚本模块
                if str(settings.BASE_DIR) not in sys.path:
                    sys.path.append(str(settings.BASE_DIR))
                module = import_module("scripts.execute_batch_task")
                
                loop = asyncio.get_running_loop()
                log_queue: asyncio.Queue[str] = asyncio.Queue()
                progress_queue: asyncio.Queue[Optional[Tuple[int, str]]] = asyncio.Queue()
                
                def log_handler(message: str):
                    loop.call_soon_threadsafe(log_queue.put_nowait, message)
                
                def progress_handler(progress: int, message: str):
                    loop.call_soon_threadsafe(progress_queue.put_nowait, (progress, message))
                
                async def log_consumer():
                    while True:
                        line = await log_queue.get()
                        if line is None:
                            break
                        cls.ensure_log_dir()
                        async with aiofiles.open(log_path, "a", encoding="utf-8", errors="replace") as log_file:
                            await log_file.write(line + "\n")
                
                async def progress_consumer():
                    last_progress = 0
                    while True:
                        item = await progress_queue.get()
                        if item is None:
                            break
                        progress, message = item
                        if progress != last_progress:
                            last_progress = progress
                            await new_task_crud.update(
                                id=task_id,
                                data={"progress": min(progress, 99)}
                            )
                            await new_db.commit()
                            logger.debug(f"任务进度更新: {progress}% - {message}")
                
                log_task = asyncio.create_task(log_consumer())
                progress_task = asyncio.create_task(progress_consumer())
                
                def run_module():
                    return module.execute_in_process(
                        log_path=log_path,
                        task_id=task_id,
                        task_type=task_type,
                        operator_metas=script_operator_metas,
                        log_handler=log_handler,
                        progress_handler=progress_handler,
                    )
                
                try:
                    return_code = await asyncio.to_thread(run_module)
                finally:
                    await log_queue.put(None)
                    await progress_queue.put(None)
                    await asyncio.gather(log_task, progress_task)
                
                # 根据返回码确定任务状态
                if return_code == 0:
                    final_status = "success"
                    error_message = None
                else:
                    # 检查是否有部分成功的情况（需要脚本输出特定格式）
                    final_status = "failed"
                    error_message = f"脚本执行失败，返回码: {return_code}"
                
                # 更新任务最终状态
                await new_task_crud.update(
                    id=task_id,
                    data={
                        "task_status": final_status,
                        "progress": 100,
                        "error_message": error_message,
                    }
                )
                await new_db.commit()
                
                await cls.write_log(log_path, f"脚本执行完成，返回码: {return_code}, 状态: {final_status}")
                logger.info(f"批次任务执行完成: task_id={task_id}, return_code={return_code}, status={final_status}")
                
            except asyncio.CancelledError:
                await new_db.rollback()
                await cls.write_log(log_path, "批次任务被取消")
                await new_task_crud.update(
                    id=task_id,
                    data={
                        "task_status": "failed",
                        "error_message": "任务被取消",
                        "progress": 100,
                    },
                )
                await new_db.commit()
                raise
            except Exception as exc:
                await new_db.rollback()
                error_msg = f"批次任务执行异常: {exc}"
                await cls.write_log(log_path, f"[ERROR] {error_msg}")
                import traceback
                error_traceback = traceback.format_exc()
                await cls.write_log(log_path, f"[ERROR] 异常堆栈:\n{error_traceback}")
                
                await new_task_crud.update(
                    id=task_id,
                    data={
                        "task_status": "failed",
                        "error_message": str(exc),
                        "progress": 100,
                    },
                )
                await new_db.commit()
                logger.error(f"批次任务执行失败: {exc}\n{error_traceback}")

