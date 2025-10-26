# -*- coding: utf-8 -*-

from typing import Dict, List, Optional, Sequence, Union, Any

from app.core.base_crud import CRUDBase
from app.api.v1.module_system.auth.schema import AuthSchema
from .model import McpModel
from .schema import McpCreateSchema, McpUpdateSchema


class McpCRUD(CRUDBase[McpModel, McpCreateSchema, McpUpdateSchema]):
    """MCP 服务器数据层"""

    def __init__(self, auth: AuthSchema) -> None:
        """
        初始化CRUD
        
        参数:
        - auth (AuthSchema): 认证信息模型
        """
        self.auth = auth
        super().__init__(model=McpModel, auth=auth)

    async def get_by_id_crud(self, id: int, preload: Optional[List[Union[str, Any]]] = None) -> Optional[McpModel]:
        """
        获取MCP服务器详情
        
        参数:
        - id (int): MCP服务器ID
        - preload (Optional[List[Union[str, Any]]]): 预加载关系，未提供时使用模型默认项
        
        返回:
        - Optional[McpModel]: MCP服务器模型实例（如果存在）
        """
        return await self.get(id=id, preload=preload)
    
    async def get_by_name_crud(self, name: str, preload: Optional[List[Union[str, Any]]] = None) -> Optional[McpModel]:
        """
        通过名称获取MCP服务器
        
        参数:
        - name (str): MCP服务器名称
        - preload (Optional[List[Union[str, Any]]]): 预加载关系，未提供时使用模型默认项
        
        返回:
        - Optional[McpModel]: MCP服务器模型实例（如果存在）
        """
        return await self.get(name=name, preload=preload)
    
    async def get_list_crud(self, search: Optional[Dict] = None, order_by: Optional[List[Dict[str, str]]] = None, preload: Optional[List[Union[str, Any]]] = None) -> Sequence[McpModel]:
        """
        列表查询MCP服务器
        
        参数:
        - search (Optional[Dict]): 查询参数字典
        - order_by (Optional[List[Dict[str, str]]]): 排序参数列表
        - preload (Optional[List[Union[str, Any]]]): 预加载关系，未提供时使用模型默认项
        
        返回:
        - Sequence[McpModel]: MCP服务器模型实例序列
        """
        return await self.list(search=search or {}, order_by=order_by or [{'id': 'asc'}], preload=preload)
    
    async def create_crud(self, data: McpCreateSchema) -> Optional[McpModel]:
        """
        创建MCP服务器
        
        参数:
        - data (McpCreateSchema): 创建MCP服务器模型
        
        返回:
        - Optional[McpModel]: 创建的MCP服务器模型实例（如果成功）
        """
        return await self.create(data=data)
    
    async def update_crud(self, id: int, data: McpUpdateSchema) -> Optional[McpModel]:
        """
        更新MCP服务器
        
        参数:
        - id (int): MCP服务器ID
        - data (McpUpdateSchema): 更新MCP服务器模型
        
        返回:
        - Optional[McpModel]: 更新的MCP服务器模型实例（如果成功）
        """
        return await self.update(id=id, data=data)
    
    async def delete_crud(self, ids: List[int]) -> None:
        """
        批量删除MCP服务器
        
        参数:
        - ids (List[int]): MCP服务器ID列表
        
        返回:
        - None
        """
        return await self.delete(ids=ids)