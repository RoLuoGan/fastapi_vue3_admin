# -*- coding: utf-8 -*-
"""
任务 CRUD
"""

from typing import Dict, List, Optional, Sequence, Union, Any

from sqlalchemy import select
from sqlalchemy.engine import Result

from app.core.base_crud import CRUDBase
from app.core.exceptions import CustomException
from app.api.v1.module_system.auth.schema import AuthSchema

from ..models import TaskModel
from .schema import TaskOutSchema


class TaskCRUD(CRUDBase[TaskModel, Dict, Dict]):
    """任务数据层"""

    def __init__(self, auth: AuthSchema) -> None:
        self.auth = auth
        super().__init__(model=TaskModel, auth=auth)

    async def get_recent_tasks_crud(
        self,
        limit: int = 20,
        preload: Optional[List[Union[str, Any]]] = None,
    ) -> Sequence[TaskModel]:
        try:
            sql = select(self.model).order_by(self.model.created_at.desc()).limit(limit)
            for opt in self._CRUDBase__loader_options(preload):
                sql = sql.options(opt)
            sql = await self._CRUDBase__filter_permissions(sql)
            result: Result = await self.db.execute(sql)
            return result.scalars().all()
        except Exception as exc:
            raise CustomException(msg=f"获取最近任务列表失败: {str(exc)}")

    async def get_by_id_crud(self, id: int, preload: Optional[List[Union[str, Any]]] = None) -> Optional[TaskModel]:
        return await self.get(id=id, preload=preload)

    async def page_crud(
        self,
        *,
        offset: int,
        limit: int,
        order_by: List[Dict[str, str]],
        search: Dict,
        out_schema = TaskOutSchema,
        preload: Optional[List[Union[str, Any]]] = None,
    ) -> Dict:
        return await self.page(
            offset=offset,
            limit=limit,
            order_by=order_by,
            search=search,
            out_schema=out_schema,
            preload=preload,
        )

    async def delete_crud(self, ids: List[int]) -> None:
        await self.delete(ids=ids)

