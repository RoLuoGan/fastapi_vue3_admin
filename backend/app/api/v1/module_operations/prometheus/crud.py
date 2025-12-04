# -*- coding: utf-8 -*-
"""
Prometheus 配置 CRUD（运维模块）
"""

from typing import List, Optional, Sequence
from sqlalchemy import select, delete
from sqlalchemy.orm import selectinload

from app.core.base_crud import CRUDBase
from app.api.v1.module_system.auth.schema import AuthSchema

from .model import PrometheusJobModel
from .schema import PrometheusJobCreateSchema, PrometheusJobUpdateSchema


class PrometheusJobCRUD(CRUDBase[PrometheusJobModel, PrometheusJobCreateSchema, PrometheusJobUpdateSchema]):
    """Prometheus Job 数据层"""

    def __init__(self, auth: AuthSchema) -> None:
        self.auth = auth
        super().__init__(model=PrometheusJobModel, auth=auth)

    async def get_by_name_crud(self, job_name: str) -> Optional[PrometheusJobModel]:
        stmt = select(PrometheusJobModel).where(PrometheusJobModel.job_name == job_name)
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def get_with_children_crud(self, job_id: int) -> Optional[PrometheusJobModel]:
        from .model import PrometheusEndpointModel
        stmt = (
            select(PrometheusJobModel)
            .where(PrometheusJobModel.id == job_id)
            .options(
                selectinload(PrometheusJobModel.endpoints).selectinload(PrometheusEndpointModel.labels),
            )
        )
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def list_with_children_crud(
        self,
        *,
        job_name: Optional[str] = None,
        is_enabled: Optional[bool] = None,
    ) -> Sequence[PrometheusJobModel]:
        from .model import PrometheusEndpointModel
        stmt = (
            select(PrometheusJobModel)
            .options(
                selectinload(PrometheusJobModel.endpoints).selectinload(PrometheusEndpointModel.labels),
            )
            .order_by(PrometheusJobModel.job_name.asc())
        )

        if job_name:
            stmt = stmt.where(PrometheusJobModel.job_name.ilike(f"%{job_name}%"))
        if is_enabled is not None:
            stmt = stmt.where(PrometheusJobModel.is_enabled == is_enabled)

        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def delete_by_ids_crud(self, ids: List[int]) -> None:
        if not ids:
            return
        stmt = delete(PrometheusJobModel).where(PrometheusJobModel.id.in_(ids))
        await self.db.execute(stmt)

