# -*- coding: utf-8 -*-

from typing import Dict, List, Optional, Sequence, Union, Any

from sqlalchemy import select
from sqlalchemy.engine import Result

from app.core.base_crud import CRUDBase
from app.core.exceptions import CustomException
from ...module_system.auth.schema import AuthSchema
from .model import ServiceModel, NodeModel, TaskModel
from .schema import ServiceCreateSchema, ServiceUpdateSchema, NodeCreateSchema, NodeUpdateSchema


class ServiceCRUD(CRUDBase[ServiceModel, ServiceCreateSchema, ServiceUpdateSchema]):
    """服务模块数据层"""

    def __init__(self, auth: AuthSchema) -> None:
        """初始化服务模块CRUD"""
        self.auth = auth
        super().__init__(model=ServiceModel, auth=auth)

    async def get_by_id_crud(self, id: int, preload: Optional[List[Union[str, Any]]] = None) -> Optional[ServiceModel]:
        """根据 id 获取服务模块信息"""
        obj = await self.get(id=id, preload=preload)
        if not obj:
            return None
        return obj

    async def get_list_crud(self, search: Optional[Dict] = None, order_by: Optional[List[Dict[str, str]]] = None, preload: Optional[List[Union[str, Any]]] = None) -> Sequence[ServiceModel]:
        """获取服务模块列表"""
        return await self.list(search=search, order_by=order_by, preload=preload)


class NodeCRUD(CRUDBase[NodeModel, NodeCreateSchema, NodeUpdateSchema]):
    """节点数据层"""

    def __init__(self, auth: AuthSchema) -> None:
        """初始化节点CRUD"""
        self.auth = auth
        super().__init__(model=NodeModel, auth=auth)

    async def get_by_id_crud(self, id: int, preload: Optional[List[Union[str, Any]]] = None) -> Optional[NodeModel]:
        """根据 id 获取节点信息"""
        obj = await self.get(id=id, preload=preload)
        if not obj:
            return None
        return obj

    async def get_list_crud(self, search: Optional[Dict] = None, order_by: Optional[List[Dict[str, str]]] = None, preload: Optional[List[Union[str, Any]]] = None) -> Sequence[NodeModel]:
        """获取节点列表"""
        return await self.list(search=search, order_by=order_by, preload=preload)


class TaskCRUD(CRUDBase[TaskModel, Dict, Dict]):
    """任务数据层"""

    def __init__(self, auth: AuthSchema) -> None:
        """初始化任务CRUD"""
        self.auth = auth
        super().__init__(model=TaskModel, auth=auth)

    async def get_recent_tasks_crud(self, limit: int = 20, preload: Optional[List[Union[str, Any]]] = None) -> Sequence[TaskModel]:
        """获取最近的任务列表"""
        try:
            # 构建查询，按创建时间倒序排列
            sql = select(self.model).order_by(self.model.created_at.desc()).limit(limit)
            
            # 应用可配置的预加载选项（使用父类的私有方法）
            for opt in self._CRUDBase__loader_options(preload):
                sql = sql.options(opt)
            
            # 应用权限过滤（访问父类的私有方法）
            sql = await self._CRUDBase__filter_permissions(sql)
            
            result: Result = await self.db.execute(sql)
            return result.scalars().all()
        except Exception as e:
            raise CustomException(msg=f"获取最近任务列表失败: {str(e)}")

