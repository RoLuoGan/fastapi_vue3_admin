# -*- coding: utf-8 -*-
"""
Prometheus 配置 Schema（运维模块）
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict, model_validator

from app.core.base_schema import BaseSchema


class PrometheusLabelItem(BaseModel):
    """标签项"""

    key: str = Field(..., min_length=1, description="标签键")
    value: str = Field(..., min_length=1, description="标签值")


class PrometheusEndpointItem(BaseModel):
    """Endpoint 输入"""

    endpoint: str = Field(..., min_length=1, description="目标地址，如 10.0.0.1:9100")
    is_enabled: bool = Field(default=True, description="是否启用")
    scheme: str = Field(default="http", description="协议（http/https）")


class PrometheusTargetItem(BaseModel):
    """Target 输入（每个 Target 包含一个 Endpoint 和一组 Labels）"""

    endpoint: PrometheusEndpointItem = Field(..., description="Endpoint 配置")
    labels: List[PrometheusLabelItem] = Field(default_factory=list, description="标签列表")


class PrometheusJobBaseSchema(BaseModel):
    """Job 基础输入"""

    job_name: str = Field(..., min_length=1, description="Job 名称")
    description: Optional[str] = Field(default=None, description="描述")
    is_enabled: bool = Field(default=True, description="是否启用")
    targets: List[PrometheusTargetItem] = Field(..., min_length=1, description="Target 列表（每个 Target 包含 Endpoint 和 Labels）")


class PrometheusJobCreateSchema(PrometheusJobBaseSchema):
    """Job 创建"""

    pass


class PrometheusJobUpdateSchema(PrometheusJobBaseSchema):
    """Job 更新"""

    pass


class PrometheusEndpointOutSchema(BaseModel):
    """Endpoint 输出"""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="Endpoint ID")
    endpoint: str = Field(..., description="Endpoint")
    is_enabled: bool = Field(default=True, description="是否启用")
    scheme: str = Field(default="http", description="协议")


class PrometheusLabelOutSchema(BaseModel):
    """标签输出"""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="标签ID")
    label_key: str = Field(..., description="标签键")
    label_value: str = Field(..., description="标签值")


class PrometheusTargetOutSchema(BaseModel):
    """Target 输出"""

    endpoint: PrometheusEndpointOutSchema = Field(..., description="Endpoint 配置")
    labels: List[PrometheusLabelItem] = Field(default_factory=list, description="标签列表")


class PrometheusJobDetailSchema(BaseSchema):
    """Job 详情响应"""

    job_name: str = Field(..., description="Job 名称")
    is_enabled: bool = Field(default=True, description="是否启用")
    targets: List[PrometheusTargetOutSchema] = Field(default_factory=list, description="Target 列表（每个 Target 包含 Endpoint 和 Labels）")

    @model_validator(mode="before")
    @classmethod
    def from_orm_obj(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        if values is None:
            return values

        if not isinstance(values, dict):
            values = {
                "id": getattr(values, "id", None),
                "job_name": getattr(values, "job_name", None),
                "description": getattr(values, "description", None),
                "is_enabled": getattr(values, "is_enabled", True),
                "endpoints": getattr(values, "endpoints", []) or [],
                "labels": getattr(values, "labels", []) or [],
                "created_at": getattr(values, "created_at", None),
                "updated_at": getattr(values, "updated_at", None),
                "creator_id": getattr(values, "creator_id", None),
                "creator": getattr(values, "creator", None),
            }

        # 将 endpoints 和 labels 转换为 targets 结构
        # 现在 labels 关联到 endpoint，每个 endpoint 都有自己的 labels
        endpoints = values.get("endpoints") or []
        
        # 构建 targets：每个 endpoint 对应自己的 labels
        targets = []
        for endpoint in endpoints:
            endpoint_dict = {
                "id": getattr(endpoint, "id", None),
                "endpoint": getattr(endpoint, "endpoint", ""),
                "is_enabled": getattr(endpoint, "is_enabled", True),
                # scheme 字段已移除，不再在导入导出中包含
            }
            # 获取该 endpoint 的 labels
            endpoint_labels = getattr(endpoint, "labels", []) or []
            labels_list = [
                PrometheusLabelItem(key=label.label_key, value=label.label_value) 
                for label in endpoint_labels
            ]
            targets.append({
                "endpoint": endpoint_dict,
                "labels": labels_list  # 每个 endpoint 使用自己的 labels
            })
        
        values["targets"] = targets
        return values


class PrometheusTreeEndpointSchema(BaseModel):
    """树形节点 - Endpoint"""

    id: int = Field(..., description="Endpoint ID")
    endpoint: str = Field(..., description="Endpoint")
    is_enabled: bool = Field(default=True, description="是否启用")
    labels_text: str = Field(default="", description="标签文本")


class PrometheusTreeJobSchema(BaseModel):
    """树形节点 - Job"""

    id: int = Field(..., description="Job ID")
    job_name: str = Field(..., description="Job 名称")
    is_enabled: bool = Field(default=True, description="是否启用")
    labels_text: str = Field(default="", description="标签文本")
    endpoints_count: int = Field(default=0, description="Endpoint 数量")
    children: List[PrometheusTreeEndpointSchema] = Field(default_factory=list, description="子节点")


class PrometheusConfigImportSchema(BaseModel):
    """JSON 导入"""

    overwrite: bool = Field(default=False, description="是否覆盖同名 Job")
    jobs: List[PrometheusJobCreateSchema] = Field(..., min_length=1, description="Job 配置列表")


class PrometheusJobExportSchema(BaseModel):
    """Job 导出格式（简化）"""

    job_name: str = Field(..., description="Job 名称")
    description: Optional[str] = Field(default=None, description="描述")
    is_enabled: bool = Field(default=True, description="是否启用")
    endpoints: List[str] = Field(..., min_length=1, description="Endpoint 列表（字符串数组）")
    labels: List[PrometheusLabelItem] = Field(default_factory=list, description="标签列表")


class PrometheusConfigImportSimpleSchema(BaseModel):
    """JSON 导入（简化格式）"""

    overwrite: bool = Field(default=False, description="是否覆盖同名 Job")
    jobs: List[PrometheusJobExportSchema] = Field(..., min_length=1, description="Job 配置列表")


class PrometheusHttpSdItemSchema(BaseModel):
    """Prometheus HTTP SD 输出"""

    targets: List[str] = Field(..., description="targets 列表")
    labels: Dict[str, Any] = Field(default_factory=dict, description="标签字典")


