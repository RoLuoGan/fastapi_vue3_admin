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

