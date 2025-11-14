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
        node = await ServerCRUD(auth).get_by_id_crud(id=id, preload=["service", "services"])
        if not node:
            raise CustomException(msg="节点不存在")
        node_dict = ServerOutSchema.model_validate(node).model_dump()
        node_dict["service_name"] = node.service.name if node.service else None
        # 返回关联的服务模块列表（多对多关系）
        services_list = []
        if node.services:
            for svc in node.services:
                services_list.append({
                    "id": svc.id,
                    "name": svc.name,
                    "code": svc.code,
                    "status": svc.status,
                    "description": svc.description,
                    "project": svc.project,
                    "module_group": svc.module_group,
                    "created_at": svc.created_at.isoformat() if svc.created_at else None,
                    "updated_at": svc.updated_at.isoformat() if svc.updated_at else None,
                })
        node_dict["services"] = services_list
        return node_dict

    @classmethod
    async def create_server_service(cls, auth: AuthSchema, data: ServerCreateSchema) -> Dict:
        # 提取service_ids用于多对多关联
        service_ids = data.service_ids or []
        
        # 排除service_ids字段创建节点
        data_dict = data.model_dump(exclude={'service_ids'}, exclude_unset=True)
        
        # 检查IP+端口唯一性
        port = data_dict.get('port') or 22
        existing = await ServerCRUD(auth).get_list_crud(
            search={"ip": data_dict['ip'], "port": port}
        )
        if existing:
            raise CustomException(msg=f"创建失败，已存在IP {data_dict['ip']}:{port} 的节点")
        
        # 如果提供了主service_id，验证其存在性
        if data_dict.get('service_id'):
            service = await ServiceCRUD(auth).get_by_id_crud(id=data_dict['service_id'])
            if not service:
                raise CustomException(msg="创建失败，服务模块不存在")
        
        # 创建节点
        node = await ServerCRUD(auth).create(data=data_dict)
        
        # 处理多对多关联
        if service_ids:
            services = []
            for sid in service_ids:
                service = await ServiceCRUD(auth).get_by_id_crud(id=sid)
                if service:
                    services.append(service)
            node.services = services
            # 刷新以加载关联数据（不提交，由外层统一管理事务）
            await auth.db.flush()
            await auth.db.refresh(node)
        
        node_dict = ServerOutSchema.model_validate(node).model_dump()
        if node.service:
            node_dict["service_name"] = node.service.name
        return node_dict

    @classmethod
    async def update_server_service(cls, auth: AuthSchema, id: int, data: ServerUpdateSchema) -> Dict:
        """
        更新服务器节点
        
        参数:
        - auth (AuthSchema): 认证信息模型
        - id (int): 节点ID
        - data (ServerUpdateSchema): 节点更新模型
        
        返回:
        - Dict: 节点详情字典
        """
        # 提取service_ids用于多对多关联
        service_ids = data.service_ids
        
        # 调用CRUD层更新方法
        node = await ServerCRUD(auth).update_with_services_crud(id=id, data=data, service_ids=service_ids)
        
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
            preload=["service", "services"],
        )

