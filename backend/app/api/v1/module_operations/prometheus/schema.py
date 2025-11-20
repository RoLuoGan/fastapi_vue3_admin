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
    metrics_path: str = Field(default="/metrics", description="采集路径")


class PrometheusJobBaseSchema(BaseModel):
    """Job 基础输入"""

    job_name: str = Field(..., min_length=1, description="Job 名称")
    description: Optional[str] = Field(default=None, description="描述")
    is_enabled: bool = Field(default=True, description="是否启用")
    scrape_interval: Optional[str] = Field(default=None, description="抓取间隔")
    honor_labels: bool = Field(default=False, description="是否保留标签")
    endpoints: List[PrometheusEndpointItem] = Field(..., min_length=1, description="Endpoint 列表")
    labels: List[PrometheusLabelItem] = Field(default_factory=list, description="标签列表")


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
    metrics_path: str = Field(default="/metrics", description="采集路径")


class PrometheusLabelOutSchema(BaseModel):
    """标签输出"""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="标签ID")
    label_key: str = Field(..., description="标签键")
    label_value: str = Field(..., description="标签值")


class PrometheusJobDetailSchema(BaseSchema):
    """Job 详情响应"""

    job_name: str = Field(..., description="Job 名称")
    is_enabled: bool = Field(default=True, description="是否启用")
    scrape_interval: Optional[str] = Field(default=None, description="抓取间隔")
    honor_labels: bool = Field(default=False, description="是否保留标签")
    endpoints: List[PrometheusEndpointOutSchema] = Field(default_factory=list, description="Endpoint 列表")
    labels: List[PrometheusLabelItem] = Field(default_factory=list, description="标签列表")

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
                "scrape_interval": getattr(values, "scrape_interval", None),
                "honor_labels": getattr(values, "honor_labels", False),
                "endpoints": getattr(values, "endpoints", []) or [],
                "labels": getattr(values, "labels", []) or [],
                "created_at": getattr(values, "created_at", None),
                "updated_at": getattr(values, "updated_at", None),
                "creator_id": getattr(values, "creator_id", None),
                "creator": getattr(values, "creator", None),
            }

        labels = values.get("labels") or []
        values["labels"] = [PrometheusLabelItem(key=label.label_key, value=label.label_value) for label in labels]

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


class PrometheusHttpSdItemSchema(BaseModel):
    """Prometheus HTTP SD 输出"""

    targets: List[str] = Field(..., description="targets 列表")
    labels: Dict[str, Any] = Field(default_factory=dict, description="标签字典")


