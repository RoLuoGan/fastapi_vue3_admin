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
from ..server.crud import ServerCRUD


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
        service_list = await ServiceCRUD(auth).get_list_crud(
            search=search_dict, 
            order_by=order_by,
            preload=["nodes"]
        )
        result: List[Dict] = []
        for service in service_list:
            service_dict = ServiceOutSchema.model_validate(service).model_dump()
            # 返回所有关联的节点（使用多对多关系），但排除节点中的services字段以避免循环引用
            nodes = []
            for node in service.nodes:
                node_dict = ServerOutSchema.model_validate(node).model_dump()
                # 移除services字段以避免循环引用
                node_dict.pop("services", None)
                nodes.append(node_dict)
            service_dict["nodes"] = nodes
            result.append(service_dict)
        return result

    @classmethod
    async def get_service_detail_service(cls, auth: AuthSchema, id: int) -> Dict:
        service = await ServiceCRUD(auth).get_by_id_crud(id=id, preload=["nodes"])
        if not service:
            raise CustomException(msg="服务模块不存在")
        service_dict = ServiceOutSchema.model_validate(service).model_dump()
        # 返回所有关联的节点（使用多对多关系）
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
            preload=["nodes"],
        )

    @classmethod
    async def create_service_service(cls, auth: AuthSchema, data: ServiceCreateSchema) -> Dict:
        exist = await ServiceCRUD(auth).get(name=data.name)
        if exist:
            raise CustomException(msg="创建失败，该服务模块已存在")
        
        # 提取节点ID列表
        node_ids = getattr(data, 'node_ids', None)
        data_dict = data.model_dump(exclude={'node_ids'})
        
        service = await ServiceCRUD(auth).create(data=data_dict)
        
        # 更新多对多关联节点
        if node_ids:
            from ..server.crud import ServerCRUD
            nodes = []
            for node_id in node_ids:
                node = await ServerCRUD(auth).get_by_id_crud(id=node_id, preload=["services"])
                if node:
                    nodes.append(node)
            service.nodes = nodes
            # 刷新以加载关联数据（不提交，由外层统一管理事务）
            await auth.db.flush()
            await auth.db.refresh(service)
        
        return ServiceOutSchema.model_validate(service).model_dump()

    @classmethod
    async def update_service_service(cls, auth: AuthSchema, id: int, data: ServiceUpdateSchema) -> Dict:
        """
        更新服务模块
        
        参数:
        - auth (AuthSchema): 认证信息模型
        - id (int): 服务模块ID
        - data (ServiceUpdateSchema): 服务模块更新模型
        
        返回:
        - Dict: 服务模块详情字典
        """
        # 提取节点ID列表
        node_ids = getattr(data, 'node_ids', None)
        
        # 调用CRUD层更新方法
        service = await ServiceCRUD(auth).update_with_nodes_crud(id=id, data=data, node_ids=node_ids)
        
        return ServiceOutSchema.model_validate(service).model_dump()

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

