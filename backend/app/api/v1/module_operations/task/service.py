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
    def _build_task_params(cls, auth: AuthSchema, validated_metas: List[Dict], task_type: str) -> Dict[str, Any]:
        """
        构建任务参数 - 新格式
        
        参数:
        - auth: 认证信息
        - validated_metas: 验证后的操作元数据列表 [{"service_id": 1, "nodes": [node_obj, ...]}, ...]
        - task_type: 任务类型 (deploy 或 restart)
        
        返回:
        - Dict: 任务参数字典，格式:
          {
            "task_type": "node_operator",
            "operator_type": "deploy",
            "operator_metas": [
              {"service_id": 1, "node_ids": [1, 2]},
              {"service_id": 2, "node_ids": [3, 4]}
            ]
          }
        """
        return {
            "task_type": "node_operator",
            "operator_type": task_type,  # deploy 或 restart
            "operator_metas": [
                {
                    "service_id": meta["service_id"],
                    "node_ids": [node.id for node in meta["nodes"]],
                }
                for meta in validated_metas
            ],
        }

    @classmethod
    async def _create_task(
        cls,
        auth: AuthSchema,
        nodes: List[Any],
        validated_metas: List[Dict],
        task_type: str,
    ) -> Dict[str, Any]:
        """
        创建单个批次任务记录（包含多个节点）
        委托日志路径构建给 TaskExecutor，委托日志写入给 TaskExecutor
        
        参数:
        - auth: 认证信息
        - nodes: 所有节点列表
        - validated_metas: 验证后的操作元数据列表 [{"service_id": 1, "nodes": [node_obj, ...]}, ...]
        - task_type: 任务类型 (deploy 或 restart)
        """
        task_crud = TaskCRUD(auth)
        
        # 使用时间戳作为日志文件名标识
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_path = TaskExecutor.build_log_path(task_type=task_type, node_ip=f"batch_{timestamp}")
        
        # 构建新格式的任务参数
        params_dict = cls._build_task_params(auth=auth, validated_metas=validated_metas, task_type=task_type)
        
        # 准备任务数据
        task_data = {
            "task_type": task_type,
            "task_status": "running",
            "progress": 0,
            "log_path": str(log_path),
            "params": json.dumps(params_dict, ensure_ascii=False),
        }
        
        task = await task_crud.create(data=task_data)
        
        # 写入初始日志
        await TaskExecutor.write_log(log_path, f"批次任务创建成功，共 {len(nodes)} 个节点")
        for idx, node in enumerate(nodes, 1):
            await TaskExecutor.write_log(log_path, f"  {idx}. {node.ip}:{node.port or 22}")
        
        await auth.db.commit()
        return {"task": task, "log_path": log_path, "nodes": nodes}

    @classmethod
    async def get_recent_tasks_service(cls, auth: AuthSchema, limit: int = 20) -> List[Dict]:
        tasks = await TaskCRUD(auth).get_recent_tasks_crud(limit=limit)
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
    async def execute_task_service(cls, auth: AuthSchema, operator_metas: List[Any], task_type: str) -> Dict:
        """
        执行任务 - 统一的任务执行入口
        
        参数:
        - auth: 认证信息
        - operator_metas: 操作元数据列表 [{"service_id": 1, "node_ids": [1, 2]}, ...]
        - task_type: 任务类型 (deploy 或 restart)
        
        返回:
        - Dict: 包含任务信息的字典
        """
        if not operator_metas:
            task_name = "部署" if task_type == "deploy" else "重启"
            raise CustomException(msg=f"请选择需要{task_name}的节点")
        
        if task_type not in ("deploy", "restart"):
            raise CustomException(msg="任务类型只能是 deploy 或 restart")

        # 根据 operator_metas 获取节点信息并验证
        nodes = []
        validated_metas = []  # 验证后的元数据（包含节点对象）
        
        for meta in operator_metas:
            service_id = meta.service_id
            node_ids = meta.node_ids
            
            service_nodes = []  # 该服务下的节点列表
            
            for node_id in node_ids:
                # 查询节点
                node = await ServerCRUD(auth).get_by_id_crud(id=node_id, preload=["service", "services"])
                if not node:
                    logger.warning(f"节点ID {node_id} 不存在，跳过")
                    continue
                
                # 验证节点是否属于该服务（检查多对多关系）
                service_ids_for_node = [s.id for s in (node.services or [])]
                if service_id not in service_ids_for_node:
                    # 如果不在多对多关系中，检查是否是主服务
                    if node.service_id != service_id:
                        logger.warning(f"节点 {node_id} 不属于服务 {service_id}，跳过")
                        continue
                
                nodes.append(node)
                service_nodes.append(node)
            
            if service_nodes:
                validated_metas.append({
                    "service_id": service_id,
                    "nodes": service_nodes,
                })

        if not nodes:
            task_name = "部署" if task_type == "deploy" else "重启"
            raise CustomException(msg=f"没有找到有效的节点进行{task_name}")

        # 创建单个批次任务（包含所有节点）
        task_record = await cls._create_task(
            auth=auth,
            nodes=nodes,
            validated_metas=validated_metas,
            task_type=task_type
        )

        task = task_record["task"]
        log_path = Path(task_record["log_path"])

        # 使用 TaskExecutor 执行批次任务，传递 operator_metas
        asyncio.create_task(
            TaskExecutor.execute_batch_task(
                base_auth=auth,
                task_id=task.id,
                log_path=log_path,
                nodes=nodes,
                task_type=task_type,
                operator_metas=validated_metas,  # 传递验证后的 operator_metas
            )
        )

        task_name = "部署" if task_type == "deploy" else "重启"
        
        return {
            "message": f"{task_name}任务已启动",
            "task_id": task.id,
            "node_count": len(nodes),
            "service_count": len(validated_metas),
            "task_type": task_type,
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

