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
    PrometheusTargetItem,
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
            # 由于 labels 现在关联到 endpoint，job 级别的 labels_text 为空或合并所有 endpoint 的 labels
            # 使用字典去重，key 为 (label_key, label_value) 元组
            unique_labels_dict = {}
            for endpoint in job.endpoints:
                for label in endpoint.labels:
                    label_key = (label.label_key, label.label_value)
                    if label_key not in unique_labels_dict:
                        unique_labels_dict[label_key] = label
            # 将去重后的 labels 转换为列表
            all_job_labels = list(unique_labels_dict.values())
            labels_text = cls._format_labels_text(all_job_labels)
            
            children = [
                PrometheusTreeEndpointSchema(
                    id=endpoint.id,
                    endpoint=endpoint.endpoint,
                    is_enabled=endpoint.is_enabled,
                    labels_text=cls._format_labels_text(endpoint.labels),  # 每个 endpoint 使用自己的 labels
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
    async def _create_job_without_detail(cls, auth: AuthSchema, data: PrometheusJobCreateSchema) -> None:
        """
        创建 Job（不返回详情，用于批量导入）
        """
        crud = PrometheusJobCRUD(auth)
        existing = await crud.get_by_name_crud(job_name=data.job_name)
        if existing:
            raise CustomException(msg=f"Job {data.job_name} 已存在")

        logger.info(f"[Prometheus] 开始创建 Job: {data.job_name}, targets 数量: {len(data.targets)}")

        job = PrometheusJobModel(
            job_name=data.job_name.strip(),
            description=data.description,
            is_enabled=data.is_enabled,
        )

        # 从 targets 中提取 endpoints，每个 endpoint 拥有自己的 labels
        for target_idx, target in enumerate(data.targets):
            endpoint_item = target.endpoint
            endpoint_value = endpoint_item.endpoint.strip()
            if not endpoint_value:
                logger.warning(f"[Prometheus] Target {target_idx + 1} 的 endpoint 为空，跳过")
                continue
            
            logger.info(f"[Prometheus] 处理 Target {target_idx + 1}: endpoint={endpoint_value}, labels 数量={len(target.labels)}")
            
            # 创建 endpoint
            endpoint_model = PrometheusEndpointModel(
                endpoint=endpoint_value,
                is_enabled=endpoint_item.is_enabled,
                scheme=endpoint_item.scheme,
            )
            
            # 为每个 endpoint 添加自己的 labels
            for label_idx, label in enumerate(target.labels):
                if label.key and label.value:
                    endpoint_model.labels.append(
                        PrometheusLabelModel(label_key=label.key, label_value=label.value)
                    )
                    logger.debug(f"[Prometheus] Target {target_idx + 1} Label {label_idx + 1}: {label.key}={label.value}")
            
            job.endpoints.append(endpoint_model)
            logger.info(f"[Prometheus] Target {target_idx + 1} 创建完成: endpoint={endpoint_value}, labels 数量={len(endpoint_model.labels)}")

        if not job.endpoints:
            raise CustomException(msg="至少需要配置一个有效的 Target")

        auth.db.add(job)
        await auth.db.flush()
        
        logger.info(f"[Prometheus] 创建 Job 成功: {job.job_name}, endpoints 数量: {len(job.endpoints)}")

    @classmethod
    async def create_job_service(cls, auth: AuthSchema, data: PrometheusJobCreateSchema, auto_commit: bool = True) -> PrometheusJobDetailSchema:
        crud = PrometheusJobCRUD(auth)
        existing = await crud.get_by_name_crud(job_name=data.job_name)
        if existing:
            raise CustomException(msg=f"Job {data.job_name} 已存在")

        logger.info(f"[Prometheus] 开始创建 Job: {data.job_name}, targets 数量: {len(data.targets)}")

        job = PrometheusJobModel(
            job_name=data.job_name.strip(),
            description=data.description,
            is_enabled=data.is_enabled,
        )

        # 从 targets 中提取 endpoints，每个 endpoint 拥有自己的 labels
        for target_idx, target in enumerate(data.targets):
            endpoint_item = target.endpoint
            endpoint_value = endpoint_item.endpoint.strip()
            if not endpoint_value:
                logger.warning(f"[Prometheus] Target {target_idx + 1} 的 endpoint 为空，跳过")
                continue
            
            logger.info(f"[Prometheus] 处理 Target {target_idx + 1}: endpoint={endpoint_value}, labels 数量={len(target.labels)}")
            
            # 创建 endpoint
            endpoint_model = PrometheusEndpointModel(
                endpoint=endpoint_value,
                is_enabled=endpoint_item.is_enabled,
                scheme=endpoint_item.scheme,
            )
            
            # 为每个 endpoint 添加自己的 labels
            for label_idx, label in enumerate(target.labels):
                if label.key and label.value:
                    endpoint_model.labels.append(
                        PrometheusLabelModel(label_key=label.key, label_value=label.value)
                    )
                    logger.debug(f"[Prometheus] Target {target_idx + 1} Label {label_idx + 1}: {label.key}={label.value}")
            
            job.endpoints.append(endpoint_model)
            logger.info(f"[Prometheus] Target {target_idx + 1} 创建完成: endpoint={endpoint_value}, labels 数量={len(endpoint_model.labels)}")

        if not job.endpoints:
            raise CustomException(msg="至少需要配置一个有效的 Target")

        auth.db.add(job)
        await auth.db.flush()
        
        # 在 commit 之前，使用 selectinload 重新加载 job 及其所有关系，确保所有数据都已加载
        # 这样可以避免在 commit 之后访问时触发延迟加载
        job_id = job.id
        stmt = (
            select(PrometheusJobModel)
            .options(
                selectinload(PrometheusJobModel.endpoints).selectinload(PrometheusEndpointModel.labels),
            )
            .where(PrometheusJobModel.id == job_id)
        )
        result = await auth.db.execute(stmt)
        job = result.scalar_one()
        
        if auto_commit:
            await auth.db.commit()

        logger.info(f"[Prometheus] 创建 Job 成功: {job.job_name}, endpoints 数量: {len(job.endpoints)}")
        return PrometheusJobDetailSchema.model_validate(job)

    @classmethod
    async def get_job_detail_service(cls, auth: AuthSchema, job_id: int) -> PrometheusJobDetailSchema:
        crud = PrometheusJobCRUD(auth)
        job = await crud.get_with_children_crud(job_id=job_id)
        if not job:
            raise CustomException(msg="Job 不存在")
        return PrometheusJobDetailSchema.model_validate(job)

    @classmethod
    async def _update_job_without_detail(cls, auth: AuthSchema, job_id: int, data: PrometheusJobCreateSchema) -> None:
        """
        更新 Job（不返回详情，用于批量导入）
        """
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

        logger.info(f"[Prometheus] 开始更新 Job ID={job_id}: {data.job_name}, targets 数量: {len(data.targets)}")

        # 清空关系集合（级联删除会自动处理 endpoints 和 labels）
        job.endpoints.clear()
        await auth.db.flush()

        # 从 targets 中提取 endpoints，每个 endpoint 拥有自己的 labels
        for target_idx, target in enumerate(data.targets):
            endpoint_item = target.endpoint
            endpoint_value = endpoint_item.endpoint.strip()
            if not endpoint_value:
                logger.warning(f"[Prometheus] Target {target_idx + 1} 的 endpoint 为空，跳过")
                continue
            
            logger.info(f"[Prometheus] 处理 Target {target_idx + 1}: endpoint={endpoint_value}, labels 数量={len(target.labels)}")
            
            # 创建 endpoint
            endpoint_model = PrometheusEndpointModel(
                endpoint=endpoint_value,
                is_enabled=endpoint_item.is_enabled,
                scheme=endpoint_item.scheme,
            )
            
            # 为每个 endpoint 添加自己的 labels
            for label_idx, label in enumerate(target.labels):
                if label.key and label.value:
                    endpoint_model.labels.append(
                        PrometheusLabelModel(label_key=label.key, label_value=label.value)
                    )
                    logger.debug(f"[Prometheus] Target {target_idx + 1} Label {label_idx + 1}: {label.key}={label.value}")
            
            job.endpoints.append(endpoint_model)
            logger.info(f"[Prometheus] Target {target_idx + 1} 创建完成: endpoint={endpoint_value}, labels 数量={len(endpoint_model.labels)}")

        if not job.endpoints:
            raise CustomException(msg="至少需要配置一个有效的 Target")

        await auth.db.flush()
        
        logger.info(f"[Prometheus] 更新 Job: {job.job_name}")

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

        logger.info(f"[Prometheus] 开始更新 Job ID={job_id}: {data.job_name}, targets 数量: {len(data.targets)}")

        # 清空关系集合（级联删除会自动处理 endpoints 和 labels）
        # 注意：由于 cascade="all, delete-orphan"，清空 endpoints 会自动删除相关的 labels
        job.endpoints.clear()
        await auth.db.flush()  # 刷新以触发级联删除

        # 从 targets 中提取 endpoints，每个 endpoint 拥有自己的 labels
        for target_idx, target in enumerate(data.targets):
            endpoint_item = target.endpoint
            endpoint_value = endpoint_item.endpoint.strip()
            if not endpoint_value:
                logger.warning(f"[Prometheus] Target {target_idx + 1} 的 endpoint 为空，跳过")
                continue
            
            logger.info(f"[Prometheus] 处理 Target {target_idx + 1}: endpoint={endpoint_value}, labels 数量={len(target.labels)}")
            
            # 创建 endpoint
            endpoint_model = PrometheusEndpointModel(
                endpoint=endpoint_value,
                is_enabled=endpoint_item.is_enabled,
                scheme=endpoint_item.scheme,
            )
            
            # 为每个 endpoint 添加自己的 labels
            for label_idx, label in enumerate(target.labels):
                if label.key and label.value:
                    endpoint_model.labels.append(
                        PrometheusLabelModel(label_key=label.key, label_value=label.value)
                    )
                    logger.debug(f"[Prometheus] Target {target_idx + 1} Label {label_idx + 1}: {label.key}={label.value}")
            
            job.endpoints.append(endpoint_model)
            logger.info(f"[Prometheus] Target {target_idx + 1} 创建完成: endpoint={endpoint_value}, labels 数量={len(endpoint_model.labels)}")

        if not job.endpoints:
            raise CustomException(msg="至少需要配置一个有效的 Target")

        await auth.db.flush()
        
        # 在 commit 之前，使用 selectinload 重新加载 job 及其所有关系，确保所有数据都已加载
        # 这样可以避免在 commit 之后访问时触发延迟加载
        job_id = job.id
        stmt = (
            select(PrometheusJobModel)
            .options(
                selectinload(PrometheusJobModel.endpoints).selectinload(PrometheusEndpointModel.labels),
            )
            .where(PrometheusJobModel.id == job_id)
        )
        result = await auth.db.execute(stmt)
        job = result.scalar_one()
        
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
            # 由于 labels 现在关联到 endpoint，我们需要构建 targets 结构
            targets = []
            for endpoint in job.endpoints:
                targets.append({
                    "endpoint": {
                        "endpoint": endpoint.endpoint,
                        "is_enabled": endpoint.is_enabled,
                    },
                    "labels": [{"key": label.label_key, "value": label.label_value} for label in endpoint.labels],
                })
            
            export_data.append(
                {
                    "job_name": job.job_name,
                    "description": job.description or "",
                    "is_enabled": job.is_enabled,
                    "targets": targets,
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
            
            # 支持新格式（targets）和旧格式（endpoints + labels）
            targets_data = job_dict.get("targets")
            if targets_data:
                # 新格式：使用 targets
                targets_list = []
                for target_dict in targets_data:
                    endpoint_dict = target_dict.get("endpoint", {})
                    if isinstance(endpoint_dict, str):
                        endpoint_item = PrometheusEndpointItem(
                            endpoint=endpoint_dict.strip(),
                            is_enabled=True,
                            scheme="http"  # 默认使用 http
                        )
                    else:
                        endpoint_item = PrometheusEndpointItem(
                            endpoint=endpoint_dict.get("endpoint", "").strip(),
                            is_enabled=endpoint_dict.get("is_enabled", True),
                            scheme="http"  # 默认使用 http，不再从导入数据读取
                        )
                    
                    labels_data = target_dict.get("labels", [])
                    labels_list = [
                        {"key": label.get("key", ""), "value": label.get("value", "")}
                        for label in labels_data
                        if label.get("key") and label.get("value")
                    ]
                    
                    if endpoint_item.endpoint:
                        targets_list.append(
                            PrometheusTargetItem(
                                endpoint=endpoint_item,
                                labels=labels_list
                            )
                        )
                
                if not targets_list:
                    raise CustomException(msg=f"Job {job_name} 至少需要一个有效的 Target")
                
                job_data = PrometheusJobCreateSchema(
                    job_name=job_name.strip(),
                    description=job_dict.get("description", "") or "",
                    is_enabled=job_dict.get("is_enabled", True),
                    targets=targets_list
                )
            else:
                # 旧格式：使用 endpoints + labels（向后兼容）
                endpoints = job_dict.get("endpoints", [])
                if endpoints and isinstance(endpoints[0], str):
                    # 简化格式：endpoints 是字符串数组
                    endpoints_list = [
                        PrometheusEndpointItem(
                            endpoint=ep.strip(),
                            is_enabled=True,
                            scheme="http"  # 默认使用 http
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
                            scheme="http"  # 默认使用 http，不再从导入数据读取
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
                
                # 将旧格式转换为新格式：每个 endpoint 使用相同的 labels
                targets_list = [
                    PrometheusTargetItem(
                        endpoint=ep,
                        labels=labels_list
                    )
                    for ep in endpoints_list
                ]
                
                job_data = PrometheusJobCreateSchema(
                    job_name=job_name.strip(),
                    description=job_dict.get("description", "") or "",
                    is_enabled=job_dict.get("is_enabled", True),
                    targets=targets_list
                )
            
            exists = await crud.get_by_name_crud(job_name=job_data.job_name)
            if exists:
                if not overwrite:
                    raise CustomException(msg=f"Job {job_data.job_name} 已存在，如需覆盖请勾选覆盖选项")
                # 更新时不需要返回详情，避免在 auto_commit=False 时触发延迟加载
                await cls._update_job_without_detail(auth, exists.id, job_data)
                updated += 1
            else:
                # 创建时不需要返回详情，避免在 auto_commit=False 时触发延迟加载
                await cls._create_job_without_detail(auth, job_data)
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
                    selectinload(PrometheusJobModel.endpoints).selectinload(PrometheusEndpointModel.labels),
                )
                .where(
                    PrometheusJobModel.is_enabled.is_(True),
                    PrometheusJobModel.job_name == job_name
                )
            )
            result = await db.execute(stmt)
            jobs = result.scalars().all()

            # 使用字典来分组相同 labels 的 endpoints
            # key: frozenset of (label_key, label_value) tuples (用于分组)
            # value: tuple (label_dict, targets_list)
            grouped_endpoints: Dict[frozenset, Dict[str, Any]] = {}
            
            for job in jobs:
                for endpoint in job.endpoints:
                    if not endpoint.is_enabled:
                        continue
                    target_value = endpoint.endpoint.strip()
                    if not target_value:
                        continue
                    
                    # 每个 endpoint 使用自己的 labels
                    label_dict = {label.label_key: label.label_value for label in endpoint.labels}
                    
                    # 将 labels 转换为可哈希的 frozenset 用于分组
                    labels_key = frozenset(label_dict.items())
                    
                    # 如果这个 labels 组合已存在，添加 target；否则创建新组
                    if labels_key in grouped_endpoints:
                        grouped_endpoints[labels_key]["targets"].append(target_value)
                    else:
                        grouped_endpoints[labels_key] = {
                            "labels": label_dict,
                            "targets": [target_value]
                        }
            
            # 将分组结果转换为 SD items
            sd_items: List[PrometheusHttpSdItemSchema] = []
            for labels_key, data in grouped_endpoints.items():
                sd_items.append(
                    PrometheusHttpSdItemSchema(
                        targets=data["targets"],
                        labels=data["labels"],
                    )
                )

            return sd_items
        finally:
            if close_session:
                await db.close()

