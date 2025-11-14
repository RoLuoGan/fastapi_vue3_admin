# -*- coding: utf-8 -*-
"""
服务器（节点）CRUD
"""

from typing import Dict, List, Optional, Sequence, Union, Any

from app.core.base_crud import CRUDBase
from app.api.v1.module_system.auth.schema import AuthSchema

from ..models import NodeModel
from .schema import ServerCreateSchema, ServerUpdateSchema


class ServerCRUD(CRUDBase[NodeModel, ServerCreateSchema, ServerUpdateSchema]):
    """节点数据层"""

    def __init__(self, auth: AuthSchema) -> None:
        self.auth = auth
        super().__init__(model=NodeModel, auth=auth)

    async def get_by_id_crud(self, id: int, preload: Optional[List[Union[str, Any]]] = None) -> Optional[NodeModel]:
        return await self.get(id=id, preload=preload)

    async def get_list_crud(
        self,
        search: Optional[Dict] = None,
        order_by: Optional[List[Dict[str, str]]] = None,
        preload: Optional[List[Union[str, Any]]] = None,
    ) -> Sequence[NodeModel]:
        return await self.list(search=search, order_by=order_by, preload=preload)

    async def page_crud(
        self,
        *,
        offset: int,
        limit: int,
        order_by: List[Dict[str, str]],
        search: Dict,
        out_schema,
        preload: Optional[List[Union[str, Any]]] = None,
    ) -> Dict:
        return await self.page(offset=offset, limit=limit, order_by=order_by, search=search, out_schema=out_schema, preload=preload)
    
    async def update_with_services_crud(self, id: int, data: ServerUpdateSchema, service_ids: Optional[List[int]] = None) -> NodeModel:
        """
        更新服务器节点（包括多对多关联的服务模块）
        
        参数:
        - id (int): 节点ID
        - data (ServerUpdateSchema): 节点更新模型
        - service_ids (Optional[List[int]]): 关联的服务模块ID列表
        
        返回:
        - NodeModel: 更新后的节点对象
        """
        from sqlalchemy import select
        from ..models import ServiceModel
        from app.core.exceptions import CustomException
        
        # 获取节点对象
        stmt = select(NodeModel).where(NodeModel.id == id)
        result = await self.db.execute(stmt)
        node = result.scalars().first()
        if not node:
            raise CustomException(msg="更新失败，该节点不存在")
        
        # 手动更新节点基本信息
        data_dict = data.model_dump(exclude={'service_ids'}, exclude_unset=True)
        
        # 检查IP+端口唯一性
        port = data_dict.get('port') if data_dict.get('port') is not None else node.port
        ip = data_dict.get('ip') or node.ip
        
        stmt = select(NodeModel).where(NodeModel.ip == ip, NodeModel.port == port, NodeModel.id != id)
        result = await self.db.execute(stmt)
        existing = result.scalars().first()
        if existing:
            raise CustomException(msg=f"更新失败，已存在IP {ip}:{port} 的节点")
        
        # 如果提供了service_id，验证其存在性
        if data_dict.get('service_id'):
            stmt = select(ServiceModel).where(ServiceModel.id == data_dict['service_id'])
            result = await self.db.execute(stmt)
            service = result.scalars().first()
            if not service:
                raise CustomException(msg="更新失败，服务模块不存在")
        
        # 更新节点属性
        for key, value in data_dict.items():
            if hasattr(node, key):
                setattr(node, key, value)
        
        # 更新多对多关联服务模块
        if service_ids is not None:
            stmt = select(ServiceModel).where(ServiceModel.id.in_(service_ids))
            result = await self.db.execute(stmt)
            services = result.scalars().all()
            node.services = list(services)
        
        # 刷新并返回（不提交，由外层统一管理事务）
        await self.db.flush()
        await self.db.refresh(node)
        
        return node

