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
from redis.asyncio.client import Redis

from app.core.exceptions import CustomException
from app.core.logger import logger
from app.api.v1.module_system.auth.schema import AuthSchema

from ..service_module.crud import ServiceCRUD
from ..server.crud import ServerCRUD  # noqa: F401
# from ..server.crud import ServerCRUD
from .crud import TaskCRUD
from .schema import TaskOutSchema, TaskDetailSchema, TaskLogSchema
from .executor import TaskExecutor
from .streamer import TaskLogStreamer


class TaskService:
    """任务管理服务层 - 只负责业务拼装和调度"""

    @classmethod
    def _build_task_params(cls, auth: AuthSchema, validated_metas: List[Dict], task_type: str, operator_type: str) -> Dict[str, Any]:
        """
        构建任务参数 - 直接透传，不做加工
        
        参数:
        - auth: 认证信息
        - validated_metas: 操作元数据列表（任意结构，直接透传）
        - task_type: 任务类型 (node_operator, server_operator 等)
        - operator_type: 操作类型 (deploy, restart, init 等)
        
        返回:
        - Dict: 任务参数字典，直接使用原始 operator_metas
        """
        # 直接透传，不做任何加工
        logger.info(f"构建任务参数 - 任务类型: {task_type}, 操作类型: {operator_type}, 操作元数据: {validated_metas}")
    
        return {
            "task_type": task_type,
            "operator_type": operator_type,
            "operator_metas": validated_metas,
        }

    @classmethod
    async def _create_task(
        cls,
        auth: AuthSchema,
        validated_metas: List[Dict],
        task_type: str,
        operator_type: str,
    ) -> Dict[str, Any]:
        """
        创建单个批次任务记录（包含多个节点）
        委托日志路径构建给 TaskExecutor，委托日志写入给 TaskExecutor
        
        参数:
        - auth: 认证信息
        - validated_metas: 操作元数据列表（任意结构，直接透传）
        - task_type: 任务类型 (node_operator, server_operator 等)
        - operator_type: 操作类型 (deploy, restart, init 等)
        """
        task_crud = TaskCRUD(auth)
        
        # 使用时间戳作为日志文件名标识
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_path = TaskExecutor.build_log_path(task_type=operator_type, node_ip=f"batch_{timestamp}")
        
        # 构建任务参数（直接透传，不做加工）
        params_dict = cls._build_task_params(
            auth=auth, 
            validated_metas=validated_metas, 
            task_type=task_type,
            operator_type=operator_type
        )
        
        # 准备任务数据
        task_data = {
            "task_type": operator_type,  # 使用 operator_type 作为 task_type 存储
            "task_status": "running",
            "progress": 0,
            "log_path": str(log_path),
            "params": json.dumps(params_dict, ensure_ascii=False),
        }
        
        task = await task_crud.create(data=task_data)
        
        # 不在这里写入初始日志，让脚本统一输出初始化信息和树形结构的日志
        
        await auth.db.commit()
        return {"task": task, "log_path": log_path}

    @classmethod
    async def get_recent_tasks_service(cls, auth: AuthSchema, limit: int = 20, task_type: Optional[str] = None) -> List[Dict]:
        tasks = await TaskCRUD(auth).get_recent_tasks_crud(limit=limit, task_type=task_type)
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
        )

    @classmethod
    async def get_task_detail_service(cls, auth: AuthSchema, task_id: int) -> Dict:
        task = await TaskCRUD(auth).get_by_id_crud(id=task_id)
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
    async def execute_task_service(
        cls,
        auth: AuthSchema,
        task_type: str,
        operator_type: str,
        operator_metas: List[Dict[str, Any]],
        redis: Optional[Redis] = None,
    ) -> Dict:
        """
        执行任务 - 统一的任务执行入口（不做参数加工，只做透传）
        
        参数:
        - auth: 认证信息
        - task_type: 任务类型 (node_operator, server_operator 等)
        - operator_type: 操作类型 (deploy, restart, init 等)
        - operator_metas: 操作元数据列表（任意结构，由客户端自定义，不做加工直接透传）
        - redis: Redis 连接（可选）
        
        返回:
        - Dict: 包含任务信息的字典
        """
        if not operator_metas:
            raise CustomException(msg="操作元数据不能为空")

        # 3. 异步执行任务
        # 注意: 这里使用 asyncio.create_task 将任务放入后台执行
        # API 会立即返回任务 ID，前端可以通过轮询或 SSE 流式获取日志
        
        # 计算节点数量 (直接从元数据计算，不查询 DB)
        node_count = 0
        for meta in operator_metas:
            if "nodes" in meta and isinstance(meta["nodes"], list):
                node_count += len(meta["nodes"])
            elif "node_ids" in meta and isinstance(meta["node_ids"], list):
                node_count += len(meta["node_ids"])

        # 创建任务记录（直接透传所有参数）
        task_record = await cls._create_task(
            auth=auth,
            validated_metas=operator_metas,  # 直接使用原始 operator_metas
            task_type=task_type,  # 传递真实的 task_type
            operator_type=operator_type  # 传递 operator_type
        )

        task = task_record["task"]
        log_path = Path(task_record["log_path"])

        # 使用 TaskExecutor 执行批次任务，直接透传所有参数
        asyncio.create_task(
            TaskExecutor.execute_batch_task(
                base_auth=auth,
                task_id=task.id,
                log_path=log_path,
                task_type=task_type,
                operator_type=operator_type,
                operator_metas=operator_metas,  # 直接透传，不做加工
                redis=redis,
            )
        )
        
        return {
            "message": "任务已启动",
            "task_id": task.id,
            "node_count": node_count,
            "task_type": task_type,
            "operator_type": operator_type,
        }

    @classmethod
    async def stream_task_log_service(
        cls,
        auth: AuthSchema,
        task_id: int,
        last_event_id: Optional[str] = None,
        redis: Optional[Any] = None,
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
            redis=redis,
        )

