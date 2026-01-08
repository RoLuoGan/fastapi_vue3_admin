# -*- coding: utf-8 -*-
"""
Celery Worker 节点 CRUD
"""

from typing import Dict, List, Optional, Sequence, Union, Any
import time

from sqlalchemy import select

from app.core.base_crud import CRUDBase
from app.api.v1.module_system.auth.schema import AuthSchema

from ..models import CeleryWorkerModel
from .schema import CeleryWorkerCreateSchema, CeleryWorkerUpdateSchema


class CeleryWorkerCRUD(CRUDBase[CeleryWorkerModel, CeleryWorkerCreateSchema, CeleryWorkerUpdateSchema]):
    """Celery Worker节点数据层"""

    def __init__(self, auth: AuthSchema) -> None:
        self.auth = auth
        super().__init__(model=CeleryWorkerModel, auth=auth)

    async def get_by_id_crud(self, id: int) -> Optional[CeleryWorkerModel]:
        return await self.get(id=id)

    async def get_list_crud(
        self,
        search: Optional[Dict] = None,
        order_by: Optional[List[Dict[str, str]]] = None,
    ) -> Sequence[CeleryWorkerModel]:
        return await self.list(search=search, order_by=order_by)

    async def page_crud(
        self,
        *,
        offset: int,
        limit: int,
        order_by: List[Dict[str, str]],
        search: Dict,
        out_schema,
    ) -> Dict:
        return await self.page(offset=offset, limit=limit, order_by=order_by, search=search, out_schema=out_schema)

    async def get_by_queue_and_ip_crud(self, queue_code: str, node_ip: str) -> Optional[CeleryWorkerModel]:
        """根据队列编码和节点IP获取Worker"""
        stmt = select(CeleryWorkerModel).where(
            CeleryWorkerModel.queue_code == queue_code,
            CeleryWorkerModel.node_ip == node_ip
        )
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def register_or_update_crud(
        self,
        queue_name: str,
        queue_code: str,
        node_ip: str,
        node_hostname: Optional[str] = None
    ) -> CeleryWorkerModel:
        """注册或更新Worker节点（心跳）"""
        existing = await self.get_by_queue_and_ip_crud(queue_code, node_ip)
        current_time = int(time.time())
        
        if existing:
            # 更新心跳（使用基类的 update 方法）
            update_data = {
                "queue_name": queue_name,
                "node_hostname": node_hostname,
                "status": True,
                "last_heartbeat": current_time
            }
            return await self.update(id=existing.id, data=update_data)
        else:
            # 创建新Worker（使用基类的 create 方法）
            create_data = {
                "queue_name": queue_name,
                "queue_code": queue_code,
                "node_ip": node_ip,
                "node_hostname": node_hostname,
                "status": True,
                "last_heartbeat": current_time
            }
            return await self.create(data=create_data)

    async def get_queues_crud(self) -> List[Dict[str, Any]]:
        """获取所有队列列表（去重）"""
        stmt = select(
            CeleryWorkerModel.queue_code,
            CeleryWorkerModel.queue_name
        ).distinct()
        result = await self.db.execute(stmt)
        rows = result.all()
        return [{"queue_code": row[0], "queue_name": row[1]} for row in rows]

    async def get_online_workers_by_queue_crud(self, queue_code: str) -> Sequence[CeleryWorkerModel]:
        """获取指定队列的在线Worker列表"""
        stmt = select(CeleryWorkerModel).where(
            CeleryWorkerModel.queue_code == queue_code,
            CeleryWorkerModel.status == True
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()


