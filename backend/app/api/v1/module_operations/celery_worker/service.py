# -*- coding: utf-8 -*-
"""
Celery Worker 节点业务逻辑
"""

from typing import List, Dict, Optional, Any

from app.core.exceptions import CustomException
from app.core.logger import logger
from app.api.v1.module_system.auth.schema import AuthSchema

from .crud import CeleryWorkerCRUD
from .schema import CeleryWorkerCreateSchema, CeleryWorkerUpdateSchema, CeleryWorkerOutSchema


class CeleryWorkerService:
    """Celery Worker节点服务层"""

    @classmethod
    async def get_list_service(
        cls,
        auth: AuthSchema,
        search: Optional[Dict] = None,
    ) -> List[Dict]:
        workers = await CeleryWorkerCRUD(auth).get_list_crud(
            search=search,
            order_by=[{"queue_code": "asc"}, {"node_ip": "asc"}]
        )
        return [CeleryWorkerOutSchema.model_validate(w).model_dump() for w in workers]

    @classmethod
    async def get_page_service(
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
        return await CeleryWorkerCRUD(auth).page_crud(
            offset=offset,
            limit=page_size,
            order_by=order,
            search=search_dict,
            out_schema=CeleryWorkerOutSchema,
        )

    @classmethod
    async def get_detail_service(cls, auth: AuthSchema, id: int) -> Dict:
        worker = await CeleryWorkerCRUD(auth).get_by_id_crud(id=id)
        if not worker:
            raise CustomException(msg="Worker节点不存在")
        return CeleryWorkerOutSchema.model_validate(worker).model_dump()

    @classmethod
    async def create_service(cls, auth: AuthSchema, data: CeleryWorkerCreateSchema) -> Dict:
        crud = CeleryWorkerCRUD(auth)
        
        # 检查是否已存在
        existing = await crud.get_by_queue_and_ip_crud(data.queue_code, data.node_ip)
        if existing:
            raise CustomException(msg=f"队列 {data.queue_code} 下已存在节点 {data.node_ip}")
        
        # 创建Worker（事务由依赖注入层自动管理，不需要显式 commit）
        worker = await crud.create(data=data.model_dump())
        return CeleryWorkerOutSchema.model_validate(worker).model_dump()

    @classmethod
    async def update_service(cls, auth: AuthSchema, id: int, data: CeleryWorkerUpdateSchema) -> Dict:
        crud = CeleryWorkerCRUD(auth)
        
        worker = await crud.get_by_id_crud(id=id)
        if not worker:
            raise CustomException(msg="Worker节点不存在")
        
        # 获取更新数据（使用 exclude_unset 以支持部分更新）
        data_dict = data.model_dump(exclude_unset=True)
        
        # 检查唯一性（如果更新了 queue_code 或 node_ip）
        queue_code = data_dict.get("queue_code") or worker.queue_code
        node_ip = data_dict.get("node_ip") or worker.node_ip
        existing = await crud.get_by_queue_and_ip_crud(queue_code, node_ip)
        if existing and existing.id != id:
            raise CustomException(msg=f"队列 {queue_code} 下已存在节点 {node_ip}")
        
        # 更新Worker（事务由依赖注入层自动管理，不需要显式 commit）
        worker = await crud.update(id=id, data=data_dict)
        return CeleryWorkerOutSchema.model_validate(worker).model_dump()

    @classmethod
    async def delete_service(cls, auth: AuthSchema, ids: List[int]) -> None:
        if len(ids) < 1:
            raise CustomException(msg="删除对象不能为空")
        # 删除Worker（事务由依赖注入层自动管理，不需要显式 commit）
        await CeleryWorkerCRUD(auth).delete_crud(ids=ids)

    @classmethod
    async def register_service(
        cls,
        auth: AuthSchema,
        queue_name: str,
        queue_code: str,
        node_ip: str,
        node_hostname: Optional[str] = None
    ) -> Dict:
        """Worker节点注册/心跳"""
        crud = CeleryWorkerCRUD(auth)
        # register_or_update_crud 已经处理了 flush 和 refresh
        # 事务由依赖注入层自动管理，不需要显式 commit
        worker = await crud.register_or_update_crud(
            queue_name=queue_name,
            queue_code=queue_code,
            node_ip=node_ip,
            node_hostname=node_hostname
        )
        logger.info(f"Celery Worker注册/心跳: {queue_code}@{node_ip}")
        return CeleryWorkerOutSchema.model_validate(worker).model_dump()

    @classmethod
    async def get_queues_service(cls, auth: AuthSchema) -> List[Dict[str, Any]]:
        """获取所有队列列表"""
        return await CeleryWorkerCRUD(auth).get_queues_crud()

    @classmethod
    async def get_online_workers_service(cls, auth: AuthSchema, queue_code: str) -> List[Dict]:
        """获取指定队列的在线Worker列表"""
        workers = await CeleryWorkerCRUD(auth).get_online_workers_by_queue_crud(queue_code)
        return [CeleryWorkerOutSchema.model_validate(w).model_dump() for w in workers]


