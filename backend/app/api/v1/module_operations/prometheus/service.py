# -*- coding: utf-8 -*-
"""
Prometheus 配置业务逻辑（运维模块）
"""

from typing import Any, Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from sqlalchemy.orm import selectinload

from app.core.exceptions import CustomException
from app.core.logger import logger
from app.api.v1.module_system.auth.schema import AuthSchema
from app.core.database import session_connect

from .crud import PrometheusJobCRUD
from .model import PrometheusJobModel, PrometheusEndpointModel, PrometheusLabelModel
from .param import PrometheusJobQueryParam
from .schema import (
    PrometheusJobCreateSchema,
    PrometheusJobUpdateSchema,
    PrometheusJobDetailSchema,
    PrometheusTreeJobSchema,
    PrometheusTreeEndpointSchema,
    PrometheusConfigImportSchema,
    PrometheusHttpSdItemSchema,
    PrometheusEndpointItem,
)


class PrometheusService:
    """Prometheus 配置服务"""

    @staticmethod
    def _format_labels_text(labels: List[PrometheusLabelModel]) -> str:
        if not labels:
            return ""
        return ", ".join([f'{label.label_key}="{label.label_value}"' for label in labels])

    @classmethod
    async def list_job_tree_service(cls, auth: AuthSchema, search: PrometheusJobQueryParam) -> List[PrometheusTreeJobSchema]:
        crud = PrometheusJobCRUD(auth)
        jobs = await crud.list_with_children_crud(
            job_name=search.job_name,
            is_enabled=search.is_enabled,
        )

        tree: List[PrometheusTreeJobSchema] = []
        for job in jobs:
            labels_text = cls._format_labels_text(job.labels)
            children = [
                PrometheusTreeEndpointSchema(
                    id=endpoint.id,
                    endpoint=endpoint.endpoint,
                    is_enabled=endpoint.is_enabled,
                    labels_text=labels_text,
                )
                for endpoint in job.endpoints
            ]
            tree.append(
                PrometheusTreeJobSchema(
                    id=job.id,
                    job_name=job.job_name,
                    is_enabled=job.is_enabled,
                    labels_text=labels_text,
                    endpoints_count=len(children),
                    children=children,
                )
            )
        return tree

    @classmethod
    async def create_job_service(cls, auth: AuthSchema, data: PrometheusJobCreateSchema, auto_commit: bool = True) -> PrometheusJobDetailSchema:
        crud = PrometheusJobCRUD(auth)
        existing = await crud.get_by_name_crud(job_name=data.job_name)
        if existing:
            raise CustomException(msg=f"Job {data.job_name} 已存在")

        job = PrometheusJobModel(
            job_name=data.job_name.strip(),
            description=data.description,
            is_enabled=data.is_enabled,
        )

        for endpoint in data.endpoints:
            endpoint_value = endpoint.endpoint.strip()
            if not endpoint_value:
                continue
            job.endpoints.append(
                PrometheusEndpointModel(
                    endpoint=endpoint_value,
                    is_enabled=endpoint.is_enabled,
                    scheme=endpoint.scheme,
                )
            )

        if not job.endpoints:
            raise CustomException(msg="至少需要配置一个有效的 Endpoint")

        for label in data.labels:
            job.labels.append(PrometheusLabelModel(label_key=label.key, label_value=label.value))

        auth.db.add(job)
        await auth.db.flush()
        await auth.db.refresh(job)
        
        if auto_commit:
            await auth.db.commit()

        logger.info(f"[Prometheus] 创建 Job: {job.job_name}")
        return PrometheusJobDetailSchema.model_validate(job)

    @classmethod
    async def get_job_detail_service(cls, auth: AuthSchema, job_id: int) -> PrometheusJobDetailSchema:
        crud = PrometheusJobCRUD(auth)
        job = await crud.get_with_children_crud(job_id=job_id)
        if not job:
            raise CustomException(msg="Job 不存在")
        return PrometheusJobDetailSchema.model_validate(job)

    @classmethod
    async def update_job_service(cls, auth: AuthSchema, job_id: int, data: PrometheusJobUpdateSchema, auto_commit: bool = True) -> PrometheusJobDetailSchema:
        crud = PrometheusJobCRUD(auth)
        job = await crud.get_with_children_crud(job_id=job_id)
        if not job:
            raise CustomException(msg="Job 不存在")

        if job.job_name != data.job_name:
            existing = await crud.get_by_name_crud(job_name=data.job_name)
            if existing:
                raise CustomException(msg=f"Job {data.job_name} 已存在")

        job.job_name = data.job_name.strip()
        job.description = data.description
        job.is_enabled = data.is_enabled

        # 显式删除旧的 endpoints 和 labels，避免唯一约束冲突
        await auth.db.execute(delete(PrometheusEndpointModel).where(PrometheusEndpointModel.job_id == job_id))
        await auth.db.execute(delete(PrometheusLabelModel).where(PrometheusLabelModel.job_id == job_id))
        await auth.db.flush()

        # 清空关系集合
        job.endpoints.clear()
        job.labels.clear()

        # 添加新的 endpoints
        for endpoint in data.endpoints:
            endpoint_value = endpoint.endpoint.strip()
            if not endpoint_value:
                continue
            job.endpoints.append(
                PrometheusEndpointModel(
                    endpoint=endpoint_value,
                    is_enabled=endpoint.is_enabled,
                    scheme=endpoint.scheme,
                )
            )
        if not job.endpoints:
            raise CustomException(msg="至少需要配置一个有效的 Endpoint")

        # 添加新的 labels
        for label in data.labels:
            job.labels.append(PrometheusLabelModel(label_key=label.key, label_value=label.value))

        await auth.db.flush()
        await auth.db.refresh(job)
        
        if auto_commit:
            await auth.db.commit()

        logger.info(f"[Prometheus] 更新 Job: {job.job_name}")
        return PrometheusJobDetailSchema.model_validate(job)

    @classmethod
    async def delete_job_service(cls, auth: AuthSchema, ids: List[int]) -> None:
        if not ids:
            return

        crud = PrometheusJobCRUD(auth)
        await crud.delete_by_ids_crud(ids=ids)
        await auth.db.commit()
        logger.info(f"[Prometheus] 删除 Job: {ids}")

    @classmethod
    async def toggle_job_status_service(cls, auth: AuthSchema, job_id: int, is_enabled: bool) -> PrometheusJobDetailSchema:
        """切换 Job 启用/禁用状态"""
        crud = PrometheusJobCRUD(auth)
        job = await crud.get_with_children_crud(job_id=job_id)
        if not job:
            raise CustomException(msg="Job 不存在")
        
        job.is_enabled = is_enabled
        await auth.db.flush()
        await auth.db.commit()
        
        logger.info(f"[Prometheus] {'启用' if is_enabled else '禁用'} Job: {job.job_name}")
        return PrometheusJobDetailSchema.model_validate(job)

    @classmethod
    async def toggle_endpoint_status_service(cls, auth: AuthSchema, endpoint_id: int, is_enabled: bool) -> None:
        """切换 Endpoint 启用/禁用状态"""
        from sqlalchemy import select
        
        stmt = select(PrometheusEndpointModel).where(PrometheusEndpointModel.id == endpoint_id)
        result = await auth.db.execute(stmt)
        endpoint = result.scalars().first()
        
        if not endpoint:
            raise CustomException(msg="Endpoint 不存在")
        
        endpoint.is_enabled = is_enabled
        await auth.db.flush()
        await auth.db.commit()
        
        logger.info(f"[Prometheus] {'启用' if is_enabled else '禁用'} Endpoint: {endpoint.endpoint}")

    @classmethod
    async def export_job_config_service(cls, auth: AuthSchema) -> List[Dict[str, Any]]:
        crud = PrometheusJobCRUD(auth)
        jobs = await crud.list_with_children_crud(job_name=None, is_enabled=None)
        export_data: List[Dict[str, Any]] = []
        for job in jobs:
            export_data.append(
                {
                    "job_name": job.job_name,
                    "description": job.description or "",
                    "is_enabled": job.is_enabled,
                    "endpoints": [endpoint.endpoint for endpoint in job.endpoints],
                    "labels": [{"key": label.label_key, "value": label.label_value} for label in job.labels],
                }
            )
        return export_data

    @classmethod
    async def import_job_config_service(cls, auth: AuthSchema, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        导入 Job 配置（支持简化格式）
        
        简化格式示例：
        {
            "overwrite": false,
            "jobs": [
                {
                    "job_name": "node_exporter",
                    "description": "",
                    "is_enabled": true,
                    "endpoints": ["192.168.1.1", "192.168.1.2"],
                    "labels": [{"key": "a", "value": "123"}]
                }
            ]
        }
        """
        crud = PrometheusJobCRUD(auth)
        created, updated = 0, 0
        overwrite = data.get("overwrite", False)
        jobs_data = data.get("jobs", [])

        for job_dict in jobs_data:
            job_name = job_dict.get("job_name")
            if not job_name:
                raise CustomException(msg="Job 名称不能为空")
            
            # 处理简化格式：endpoints 可能是字符串数组或对象数组
            endpoints = job_dict.get("endpoints", [])
            if endpoints and isinstance(endpoints[0], str):
                # 简化格式：endpoints 是字符串数组
                endpoints_list = [
                    PrometheusEndpointItem(
                        endpoint=ep.strip(),
                        is_enabled=True,
                        scheme="http"
                    )
                    for ep in endpoints
                    if ep and ep.strip()
                ]
            else:
                # 标准格式：endpoints 是对象数组
                endpoints_list = [
                    PrometheusEndpointItem(
                        endpoint=ep.get("endpoint", "").strip(),
                        is_enabled=ep.get("is_enabled", True),
                        scheme=ep.get("scheme", "http")
                    )
                    for ep in endpoints
                    if ep.get("endpoint", "").strip()
                ]
            
            if not endpoints_list:
                raise CustomException(msg=f"Job {job_name} 至少需要一个有效的 Endpoint")
            
            # 处理 labels
            labels_data = job_dict.get("labels", [])
            labels_list = [
                {"key": label.get("key", ""), "value": label.get("value", "")}
                for label in labels_data
                if label.get("key") and label.get("value")
            ]
            
            job_data = PrometheusJobCreateSchema(
                job_name=job_name.strip(),
                description=job_dict.get("description", "") or "",
                is_enabled=job_dict.get("is_enabled", True),
                endpoints=endpoints_list,
                labels=labels_list
            )
            
            exists = await crud.get_by_name_crud(job_name=job_data.job_name)
            if exists:
                if not overwrite:
                    raise CustomException(msg=f"Job {job_data.job_name} 已存在，如需覆盖请勾选覆盖选项")
                await cls.update_job_service(auth, exists.id, PrometheusJobUpdateSchema(**job_data.model_dump()), auto_commit=False)
                updated += 1
            else:
                await cls.create_job_service(auth, job_data, auto_commit=False)
                created += 1

        # 批量处理完成后统一提交
        await auth.db.commit()
        return {"created": created, "updated": updated}

    @classmethod
    async def http_sd_config_service(cls, job_name: str, db: Optional[AsyncSession] = None) -> List[PrometheusHttpSdItemSchema]:
        """
        Prometheus HTTP SD 输出
        
        参数:
        - job_name (str): Job 名称，用于过滤
        - db (Optional[AsyncSession]): 数据库会话，如果为 None 则创建新会话
        """

        close_session = False
        if db is None:
            db = session_connect()
            close_session = True

        try:
            stmt = (
                select(PrometheusJobModel)
                .options(
                    selectinload(PrometheusJobModel.endpoints),
                    selectinload(PrometheusJobModel.labels),
                )
                .where(
                    PrometheusJobModel.is_enabled.is_(True),
                    PrometheusJobModel.job_name == job_name
                )
            )
            result = await db.execute(stmt)
            jobs = result.scalars().all()

            sd_items: List[PrometheusHttpSdItemSchema] = []
            for job in jobs:
                label_dict = {label.label_key: label.label_value for label in job.labels}
                for endpoint in job.endpoints:
                    if not endpoint.is_enabled:
                        continue
                    target_value = endpoint.endpoint.strip()
                    if not target_value:
                        continue
                    labels = dict(label_dict)
                    # 只保留用户自定义标签，不包含 endpoint_id、job_id、__scheme__、__metrics_path__
                    sd_items.append(
                        PrometheusHttpSdItemSchema(
                            targets=[target_value],
                            labels=labels,
                        )
                    )

            return sd_items
        finally:
            if close_session:
                await db.close()

