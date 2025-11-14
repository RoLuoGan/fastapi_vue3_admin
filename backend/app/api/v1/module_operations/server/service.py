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
from ..service_module.schema import ServiceOutSchema


class ServerService:
    """服务器节点业务"""

    @classmethod
    async def get_server_detail_service(cls, auth: AuthSchema, id: int) -> Dict:
        node = await ServerCRUD(auth).get_by_id_crud(id=id, preload=["service"])
        if not node:
            raise CustomException(msg="节点不存在")
        node_dict = ServerOutSchema.model_validate(node).model_dump()
        node_dict["service_name"] = node.service.name if node.service else None
        # 返回关联的服务模块列表（用于前端显示）
        # 注意：不直接序列化 node.service，因为 ServiceOutSchema 包含 nodes 字段，
        # 需要预加载 nodes 关系，但在这个场景下我们不需要节点列表
        if node.service:
            # 手动构建服务数据，排除 nodes 字段，避免异步加载问题
            service_dict = {
                "id": node.service.id,
                "name": node.service.name,
                "code": node.service.code,
                "status": node.service.status,
                "description": node.service.description,
                "project": node.service.project,
                "module_group": node.service.module_group,
                "created_at": node.service.created_at.isoformat() if node.service.created_at else None,
                "updated_at": node.service.updated_at.isoformat() if node.service.updated_at else None,
                "nodes": None,  # 不包含节点列表，避免异步加载问题
            }
            node_dict["services"] = [service_dict]
        else:
            node_dict["services"] = []
        return node_dict

    @classmethod
    async def create_server_service(cls, auth: AuthSchema, data: ServerCreateSchema) -> Dict:
        # 提取并排除service_ids字段（如果存在）
        data_dict = data.model_dump(exclude={'service_ids'}, exclude_unset=True)
        
        # 如果提供了service_id，验证服务模块是否存在
        if data_dict.get('service_id'):
            service = await ServiceCRUD(auth).get_by_id_crud(id=data_dict['service_id'])
            if not service:
                raise CustomException(msg="创建失败，服务模块不存在")

            port = data_dict.get('port') or 22
            existing = await ServerCRUD(auth).get_list_crud(
                search={"service_id": data_dict['service_id'], "ip": data_dict['ip'], "port": port}
            )
            if existing:
                raise CustomException(msg=f"创建失败，服务模块下已存在IP {data_dict['ip']}:{port} 的节点")

        node = await ServerCRUD(auth).create(data=data_dict)
        node_dict = ServerOutSchema.model_validate(node).model_dump()
        if node.service:
            node_dict["service_name"] = node.service.name
        return node_dict

    @classmethod
    async def update_server_service(cls, auth: AuthSchema, id: int, data: ServerUpdateSchema) -> Dict:
        node = await ServerCRUD(auth).get_by_id_crud(id=id)
        if not node:
            raise CustomException(msg="更新失败，该节点不存在")

        # 提取并排除service_ids字段（如果存在）
        data_dict = data.model_dump(exclude={'service_ids'}, exclude_unset=True)
        
        # 如果提供了service_id，验证服务模块是否存在
        if data_dict.get('service_id'):
            service = await ServiceCRUD(auth).get_by_id_crud(id=data_dict['service_id'])
            if not service:
                raise CustomException(msg="更新失败，服务模块不存在")

        port = data_dict.get('port') or 22
        ip = data_dict.get('ip') or node.ip
        service_id = data_dict.get('service_id')
        
        if service_id:
            existing = await ServerCRUD(auth).get_list_crud(
                search={"service_id": service_id, "ip": ip, "port": port}
            )
            existing = [item for item in existing if item.id != id]
            if existing:
                raise CustomException(msg=f"更新失败，服务模块下已存在IP {ip}:{port} 的节点")

        node = await ServerCRUD(auth).update(id=id, data=data_dict)
        node_dict = ServerOutSchema.model_validate(node).model_dump()
        if node.service:
            node_dict["service_name"] = node.service.name
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

