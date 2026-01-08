# -*- coding: utf-8 -*-
"""
脚本管理 CRUD
"""

from typing import Dict, List, Optional, Sequence
import json

from sqlalchemy import select

from app.core.base_crud import CRUDBase
from app.api.v1.module_system.auth.schema import AuthSchema

from ..models import ScriptModel
from .schema import ScriptCreateSchema, ScriptUpdateSchema


class ScriptCRUD(CRUDBase[ScriptModel, ScriptCreateSchema, ScriptUpdateSchema]):
    """脚本管理数据层"""

    def __init__(self, auth: AuthSchema) -> None:
        self.auth = auth
        super().__init__(model=ScriptModel, auth=auth)

    async def get_by_id_crud(self, id: int) -> Optional[ScriptModel]:
        return await self.get(id=id)

    async def get_list_crud(
        self,
        search: Optional[Dict] = None,
        order_by: Optional[List[Dict[str, str]]] = None,
    ) -> Sequence[ScriptModel]:
        return await self.list(search=search, order_by=order_by)

    async def page_crud(
        self,
        *,
        offset: int,
        limit: int,
        order_by: List[Dict[str, str]],
        search: Dict,
        out_schema,
    ) -> Dict:
        return await self.page(offset=offset, limit=limit, order_by=order_by, search=search, out_schema=out_schema)

    async def get_by_name_crud(self, name: str) -> Optional[ScriptModel]:
        """根据名称获取脚本"""
        stmt = select(ScriptModel).where(ScriptModel.name == name)
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def create_script_crud(self, data: ScriptCreateSchema) -> ScriptModel:
        """创建脚本（处理params_schema序列化）"""
        data_dict = data.model_dump()
        # 序列化 params_schema
        if data_dict.get("params_schema"):
            data_dict["params_schema"] = json.dumps(data_dict["params_schema"], ensure_ascii=False)
        else:
            data_dict["params_schema"] = None
        
        # 使用基类的 create 方法（它已经处理了 flush 和 refresh，不调用 commit）
        return await self.create(data=data_dict)

    async def update_script_crud(self, id: int, data: ScriptUpdateSchema) -> ScriptModel:
        """更新脚本（处理params_schema序列化）"""
        data_dict = data.model_dump(exclude_unset=True)
        # 序列化 params_schema
        if "params_schema" in data_dict:
            if data_dict["params_schema"]:
                data_dict["params_schema"] = json.dumps(data_dict["params_schema"], ensure_ascii=False)
            else:
                data_dict["params_schema"] = None
        
        # 使用基类的 update 方法（它已经处理了 flush 和 refresh，不调用 commit）
        return await self.update(id=id, data=data_dict)


