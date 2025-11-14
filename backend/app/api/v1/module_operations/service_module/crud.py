# -*- coding: utf-8 -*-
"""
服务模块 CRUD
"""

from typing import Dict, List, Optional, Sequence, Union, Any

from app.core.base_crud import CRUDBase
from app.api.v1.module_system.auth.schema import AuthSchema

from ..models import ServiceModel
from .schema import ServiceCreateSchema, ServiceUpdateSchema


class ServiceCRUD(CRUDBase[ServiceModel, ServiceCreateSchema, ServiceUpdateSchema]):
    """服务模块数据层"""

    def __init__(self, auth: AuthSchema) -> None:
        self.auth = auth
        super().__init__(model=ServiceModel, auth=auth)

    async def get_by_id_crud(self, id: int, preload: Optional[List[Union[str, Any]]] = None) -> Optional[ServiceModel]:
        return await self.get(id=id, preload=preload)

    async def get_list_crud(
        self,
        search: Optional[Dict] = None,
        order_by: Optional[List[Dict[str, str]]] = None,
        preload: Optional[List[Union[str, Any]]] = None,
    ) -> Sequence[ServiceModel]:
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
    
    async def update_with_nodes_crud(self, id: int, data: ServiceUpdateSchema, node_ids: Optional[List[int]] = None) -> ServiceModel:
        """
        更新服务模块（包括多对多关联的节点）
        
        参数:
        - id (int): 服务模块ID
        - data (ServiceUpdateSchema): 服务模块更新模型
        - node_ids (Optional[List[int]]): 关联的节点ID列表
        
        返回:
        - ServiceModel: 更新后的服务模块对象
        """
        from sqlalchemy import select
        from ..models import NodeModel
        
        # 检查名称重复
        if data.name:
            stmt = select(ServiceModel).where(ServiceModel.name == data.name, ServiceModel.id != id)
            result = await self.db.execute(stmt)
            exist_service = result.scalars().first()
            if exist_service:
                from app.core.exceptions import CustomException
                raise CustomException(msg="更新失败，服务模块名称重复")
        
        # 获取服务对象
        stmt = select(ServiceModel).where(ServiceModel.id == id)
        result = await self.db.execute(stmt)
        service = result.scalars().first()
        if not service:
            from app.core.exceptions import CustomException
            raise CustomException(msg="更新失败，该服务模块不存在")
        
        # 手动更新服务基本信息
        data_dict = data.model_dump(exclude={'node_ids', 'id'}, exclude_unset=True)
        for key, value in data_dict.items():
            if hasattr(service, key):
                setattr(service, key, value)
        
        # 更新多对多关联节点
        if node_ids is not None:
            stmt = select(NodeModel).where(NodeModel.id.in_(node_ids))
            result = await self.db.execute(stmt)
            nodes = result.scalars().all()
            service.nodes = list(nodes)
        
        # 刷新并返回（不提交，由外层统一管理事务）
        await self.db.flush()
        await self.db.refresh(service)
        
        return service

