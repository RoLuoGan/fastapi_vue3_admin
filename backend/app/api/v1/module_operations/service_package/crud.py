from typing import List, Optional, Dict, Sequence, Union, Any
from sqlalchemy import select, desc
from app.core.base_crud import CRUDBase
from app.api.v1.module_system.auth.schema import AuthSchema
from app.api.v1.module_operations.models import ServicePackageModel
from .schema import ServicePackageCreateSchema, ServicePackageUpdateSchema

class ServicePackageCRUD(CRUDBase[ServicePackageModel, ServicePackageCreateSchema, ServicePackageUpdateSchema]):
    """服务软件包数据层"""
    
    def __init__(self, auth: AuthSchema) -> None:
        """
        初始化服务软件包CRUD
        
        参数:
        - auth (AuthSchema): 认证信息模型
        """
        self.auth = auth
        super().__init__(model=ServicePackageModel, auth=auth)
    
    async def get_obj_by_id_crud(self, id: int, preload: Optional[List[Union[str, Any]]] = None) -> Optional[ServicePackageModel]:
        """
        获取服务软件包详情
        
        参数:
        - id (int): 服务软件包ID
        - preload (Optional[List[Union[str, Any]]]): 预加载关系，未提供时使用模型默认项
        
        返回:
        - Optional[ServicePackageModel]: 服务软件包模型实例
        """
        return await self.get(id=id, preload=preload)
    
    async def get_obj_list_crud(self, search: Optional[Dict] = None, order_by: Optional[List[Dict[str, str]]] = None, preload: Optional[List[Union[str, Any]]] = None) -> Sequence[ServicePackageModel]:
        """
        获取服务软件包列表
        
        参数:
        - search (Dict | None): 查询参数对象。
        - order_by (List[Dict[str, str]] | None): 排序参数列表。
        - preload (Optional[List[Union[str, Any]]]): 预加载关系，未提供时使用模型默认项
        
        返回:
        - Sequence[ServicePackageModel]: 服务软件包模型实例列表
        """
        return await self.list(search=search, order_by=order_by, preload=preload)
    
    async def create_obj_crud(self, data: ServicePackageCreateSchema) -> Optional[ServicePackageModel]:
        """
        创建服务软件包
        
        参数:
        - data (ServicePackageCreateSchema): 创建服务软件包负载模型
        
        返回:
        - Optional[ServicePackageModel]: 服务软件包模型实例
        """
        return await self.create(data=data)
    
    async def update_obj_crud(self, id: int, data: ServicePackageUpdateSchema) -> Optional[ServicePackageModel]:
        """
        更新服务软件包
        
        参数:
        - id (int): 服务软件包ID
        - data (ServicePackageUpdateSchema): 更新服务软件包负载模型
        
        返回:
        - Optional[ServicePackageModel]: 服务软件包模型实例
        """
        return await self.update(id=id, data=data)
    
    async def delete_obj_crud(self, ids: List[int]) -> None:
        """
        删除服务软件包
        
        参数:
        - ids (List[int]): 服务软件包ID列表
        
        返回:
        - None
        """
        return await self.delete(ids=ids)

    async def get_packages_by_service(self, service_id: int) -> List[ServicePackageModel]:
        stmt = select(self.model).where(self.model.service_id == service_id).order_by(desc(self.model.created_at))
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_by_service_and_version(self, service_id: int, version: str) -> Optional[ServicePackageModel]:
        stmt = select(self.model).where(self.model.service_id == service_id, self.model.version == version)
        result = await self.db.execute(stmt)
        return result.scalars().first()
