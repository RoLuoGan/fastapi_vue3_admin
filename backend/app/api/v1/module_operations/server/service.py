# -*- coding: utf-8 -*-
"""
服务器（节点）业务逻辑
"""

from typing import Dict, List, Optional

from app.core.exceptions import CustomException
from app.api.v1.module_system.auth.schema import AuthSchema

from ..service_module.crud import ServiceCRUD
from .crud import ServerCRUD
from .schema import ServerCreateSchema, ServerUpdateSchema, ServerOutSchema


class ServerService:
    """服务器节点业务"""

    @classmethod
    async def get_server_detail_service(cls, auth: AuthSchema, id: int) -> Dict:
        node = await ServerCRUD(auth).get_by_id_crud(id=id)
        if not node:
            raise CustomException(msg="节点不存在")
        node_dict = ServerOutSchema.model_validate(node).model_dump()
        node_dict["service_name"] = node.service.name if node.service else None
        return node_dict

    @classmethod
    async def create_server_service(cls, auth: AuthSchema, data: ServerCreateSchema) -> Dict:
        service = await ServiceCRUD(auth).get_by_id_crud(id=data.service_id)
        if not service:
            raise CustomException(msg="创建失败，服务模块不存在")

        port = data.port or 22
        existing = await ServerCRUD(auth).get_list_crud(
            search={"service_id": data.service_id, "ip": data.ip, "port": port}
        )
        if existing:
            raise CustomException(msg=f"创建失败，服务模块下已存在IP {data.ip}:{port} 的节点")

        node = await ServerCRUD(auth).create(data=data)
        node_dict = ServerOutSchema.model_validate(node).model_dump()
        node_dict["service_name"] = service.name
        return node_dict

    @classmethod
    async def update_server_service(cls, auth: AuthSchema, id: int, data: ServerUpdateSchema) -> Dict:
        node = await ServerCRUD(auth).get_by_id_crud(id=id)
        if not node:
            raise CustomException(msg="更新失败，该节点不存在")

        service = await ServiceCRUD(auth).get_by_id_crud(id=data.service_id)
        if not service:
            raise CustomException(msg="更新失败，服务模块不存在")

        port = data.port or 22
        existing = await ServerCRUD(auth).get_list_crud(
            search={"service_id": data.service_id, "ip": data.ip, "port": port}
        )
        existing = [item for item in existing if item.id != id]
        if existing:
            raise CustomException(msg=f"更新失败，服务模块下已存在IP {data.ip}:{port} 的节点")

        node = await ServerCRUD(auth).update(id=id, data=data)
        node_dict = ServerOutSchema.model_validate(node).model_dump()
        node_dict["service_name"] = service.name
        return node_dict

    @classmethod
    async def delete_server_service(cls, auth: AuthSchema, ids: List[int]) -> None:
        if len(ids) < 1:
            raise CustomException(msg="删除失败，删除对象不能为空")
        for node_id in ids:
            node = await ServerCRUD(auth).get_by_id_crud(id=node_id)
            if not node:
                raise CustomException(msg="删除失败，该节点不存在")
        await ServerCRUD(auth).delete(ids=ids)

    @classmethod
    async def get_server_page_service(
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
        return await ServerCRUD(auth).page_crud(
            offset=offset,
            limit=page_size,
            order_by=order,
            search=search_dict,
            out_schema=ServerOutSchema,
            preload=["service"],
        )

