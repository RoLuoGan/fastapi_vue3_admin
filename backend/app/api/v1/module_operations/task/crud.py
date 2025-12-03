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
        task_type: Optional[str] = None,
        preload: Optional[List[Union[str, Any]]] = None,
    ) -> Sequence[TaskModel]:
        try:
            sql = select(self.model).order_by(self.model.created_at.desc())
            
            # 如果指定了任务类型，添加过滤条件
            if task_type:
                sql = sql.where(self.model.task_type == task_type)
            
            sql = sql.limit(limit)
            
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
        # 处理 task_type 和 operator_type 的过滤（从 params JSON 字段中提取）
        search_dict = search.copy()
        task_type_filter = search_dict.pop("task_type", None)
        operator_type_filter = search_dict.pop("operator_type", None)
        
        # 构建基础查询
        result = await self.page(
            offset=offset,
            limit=limit,
            order_by=order_by,
            search=search_dict,
            out_schema=out_schema,
            preload=preload,
        )
        
        # 如果指定了 task_type 或 operator_type，需要从 params JSON 中过滤
        if task_type_filter or operator_type_filter:
            import json
            filtered_items = []
            for item in result.get("items", []):
                # 解析 params JSON (item 已经是字典，不是 ORM 对象)
                item_params = item.get("params") if isinstance(item, dict) else getattr(item, "params", None)
                params = {}
                
                if isinstance(item_params, dict):
                    params = item_params
                elif isinstance(item_params, str):
                    try:
                        params = json.loads(item_params)
                    except:
                        params = {}
                
                # 检查 task_type 过滤
                if task_type_filter:
                    if params.get("task_type") != task_type_filter:
                        continue
                
                # 检查 operator_type 过滤
                if operator_type_filter:
                    if params.get("operator_type") != operator_type_filter:
                        continue
                
                filtered_items.append(item)
            
            # 更新结果
            result["items"] = filtered_items
            result["total"] = len(filtered_items)
        
        return result

    async def delete_crud(self, ids: List[int]) -> None:
        await self.delete(ids=ids)

