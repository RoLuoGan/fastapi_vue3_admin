# -*- coding: utf-8 -*-
"""
Celery Worker 节点 Schema 定义
"""

from typing import Optional
from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.core.base_schema import BaseSchema


class CeleryWorkerCreateSchema(BaseModel):
    """Celery Worker节点创建模型"""
    queue_name: str = Field(..., max_length=100, description="执行队列名称")
    queue_code: str = Field(..., max_length=50, description="执行队列编码")
    node_ip: str = Field(..., max_length=50, description="节点IP")
    node_hostname: Optional[str] = Field(default=None, max_length=100, description="节点主机名")
    status: bool = Field(default=True, description="是否在线(True:在线 False:离线)")

    @field_validator("queue_code")
    @classmethod
    def validate_queue_code(cls, value: str) -> str:
        if not value or len(value.strip()) == 0:
            raise ValueError("执行队列编码不能为空")
        import re
        if not re.match(r'^[a-zA-Z][a-zA-Z0-9_]*$', value):
            raise ValueError("队列编码必须以字母开头，只能包含字母、数字和下划线")
        return value.lower()

    @field_validator("node_ip")
    @classmethod
    def validate_ip(cls, value: str) -> str:
        if not value or len(value.strip()) == 0:
            raise ValueError("节点IP地址不能为空")
        import re
        ip_pattern = r"^(\d{1,3}\.){3}\d{1,3}$"
        if not re.match(ip_pattern, value):
            raise ValueError("IP地址格式不正确")
        parts = value.split(".")
        for part in parts:
            if not 0 <= int(part) <= 255:
                raise ValueError("IP地址段必须在0-255范围内")
        return value


class CeleryWorkerUpdateSchema(CeleryWorkerCreateSchema):
    """Celery Worker节点更新模型"""
    ...


class CeleryWorkerRegisterSchema(BaseModel):
    """Celery Worker节点注册模型（Worker自动注册用）"""
    queue_name: str = Field(..., max_length=100, description="执行队列名称")
    queue_code: str = Field(..., max_length=50, description="执行队列编码")
    node_ip: str = Field(..., max_length=50, description="节点IP")
    node_hostname: Optional[str] = Field(default=None, max_length=100, description="节点主机名")


class CeleryWorkerOutSchema(CeleryWorkerCreateSchema, BaseSchema):
    """Celery Worker节点响应模型"""
    model_config = {"from_attributes": True}

    last_heartbeat: Optional[int] = Field(default=None, description="最后心跳时间戳")
    last_heartbeat_time: Optional[str] = Field(default=None, description="最后心跳时间（格式化）")

    @classmethod
    def model_validate(cls, obj, **kwargs):
        instance = super().model_validate(obj, **kwargs)
        # 格式化心跳时间
        if instance.last_heartbeat:
            instance.last_heartbeat_time = datetime.fromtimestamp(instance.last_heartbeat).strftime("%Y-%m-%d %H:%M:%S")
        return instance


