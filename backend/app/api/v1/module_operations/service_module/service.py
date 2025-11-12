# -*- coding: utf-8 -*-
"""
服务模块领域服务
"""

from typing import List, Dict, Optional

from app.core.exceptions import CustomException
from app.api.v1.module_system.auth.schema import AuthSchema

from .crud import ServiceCRUD
from .schema import ServiceCreateSchema, ServiceUpdateSchema, ServiceOutSchema
from ..server.schema import ServerOutSchema


class ServiceService:
    """服务模块业务逻辑"""

    @classmethod
    async def get_service_tree_service(
        cls,
        auth: AuthSchema,
        search: Optional[dict] = None,
        order_by: Optional[List[Dict]] = None,
    ) -> List[Dict]:
        search_dict = search or {}
        service_list = await ServiceCRUD(auth).get_list_crud(search=search_dict, order_by=order_by)
        result: List[Dict] = []
        for service in service_list:
            service_dict = ServiceOutSchema.model_validate(service).model_dump()
            nodes = [
                ServerOutSchema.model_validate(node).model_dump()
                for node in service.nodes
            ]
            service_dict["nodes"] = nodes
            result.append(service_dict)
        return result

    @classmethod
    async def get_service_detail_service(cls, auth: AuthSchema, id: int) -> Dict:
        service = await ServiceCRUD(auth).get_by_id_crud(id=id)
        if not service:
            raise CustomException(msg="服务模块不存在")
        service_dict = ServiceOutSchema.model_validate(service).model_dump()
        service_dict["nodes"] = [
            ServerOutSchema.model_validate(node).model_dump()
            for node in service.nodes
        ]
        return service_dict

    @classmethod
    async def get_service_page_service(
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
        search_dict = search.__dict__ if hasattr(search, "__dict__") else (search or {})
        order = order_by or [{"created_at": "desc"}]
        return await ServiceCRUD(auth).page_crud(
            offset=offset,
            limit=page_size,
            order_by=order,
            search=search_dict,
            out_schema=ServiceOutSchema,
            preload=None,
        )

    @classmethod
    async def create_service_service(cls, auth: AuthSchema, data: ServiceCreateSchema) -> Dict:
        exist = await ServiceCRUD(auth).get(name=data.name)
        if exist:
            raise CustomException(msg="创建失败，该服务模块已存在")
        service = await ServiceCRUD(auth).create(data=data)
        return ServiceOutSchema.model_validate(service).model_dump()

    @classmethod
    async def update_service_service(cls, auth: AuthSchema, id: int, data: ServiceUpdateSchema) -> Dict:
        service = await ServiceCRUD(auth).get_by_id_crud(id=id)
        if not service:
            raise CustomException(msg="更新失败，该服务模块不存在")
        exist_service = await ServiceCRUD(auth).get(name=data.name)
        if exist_service and exist_service.id != id:
            raise CustomException(msg="更新失败，服务模块名称重复")
        updated = await ServiceCRUD(auth).update(id=id, data=data)
        return ServiceOutSchema.model_validate(updated).model_dump()

    @classmethod
    async def delete_service_service(cls, auth: AuthSchema, ids: List[int]) -> None:
        if len(ids) < 1:
            raise CustomException(msg="删除失败，删除对象不能为空")
        for service_id in ids:
            service = await ServiceCRUD(auth).get_by_id_crud(id=service_id, preload=["nodes"])
            if not service:
                raise CustomException(msg="删除失败，该服务模块不存在")
            if service.nodes and len(service.nodes) > 0:
                raise CustomException(msg=f'删除失败，服务模块"{service.name}"下存在节点，请先删除节点')
        await ServiceCRUD(auth).delete(ids=ids)

