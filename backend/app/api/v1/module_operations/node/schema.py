# -*- coding: utf-8 -*-
"""
服务节点管理模型Schema模块
"""

from typing import Optional, List
from pydantic import BaseModel, Field, field_validator, model_validator

from app.core.base_schema import BaseSchema


class ServiceCreateSchema(BaseModel):
    """服务模块创建模型"""
    name: str = Field(..., max_length=100, description="服务模块名称")
    code: Optional[str] = Field(default=None, max_length=50, description="服务模块编码")
    status: bool = Field(default=True, description="是否启用(True:启用 False:禁用)")
    description: Optional[str] = Field(default=None, max_length=255, description="备注说明")

    @field_validator('name')
    @classmethod
    def validate_name(cls, value: str):
        if not value or len(value.strip()) == 0:
            raise ValueError("服务模块名称不能为空")
        value = value.replace(" ", "")
        return value

    @field_validator('code')
    @classmethod
    def validate_code(cls, value: Optional[str]):
        if value is None:
            return value
        v = value.strip()
        if v == "":
            return None
        import re
        if not re.match(r'^[A-Za-z][A-Za-z0-9_]*$', v):
            raise ValueError("服务模块编码必须以字母开头，且仅包含字母/数字/下划线")
        return v


class ServiceUpdateSchema(ServiceCreateSchema):
    """服务模块更新模型"""
    ...


class ServiceOutSchema(ServiceCreateSchema, BaseSchema):
    """服务模块响应模型"""
    model_config = {"from_attributes": True}
    
    nodes: Optional[List["NodeOutSchema"]] = Field(default=None, description="节点列表")


class NodeCreateSchema(BaseModel):
    """节点创建模型"""
    service_id: int = Field(..., ge=1, description="服务模块ID")
    ip: str = Field(..., max_length=50, description="节点IP地址")
    port: Optional[int] = Field(default=22, ge=1, le=65535, description="端口号")
    status: bool = Field(default=True, description="是否启用(True:启用 False:禁用)")
    description: Optional[str] = Field(default=None, max_length=255, description="备注说明")

    @field_validator('ip')
    @classmethod
    def validate_ip(cls, value: str):
        if not value or len(value.strip()) == 0:
            raise ValueError("节点IP地址不能为空")
        import re
        # 简单的IP地址格式验证
        ip_pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
        if not re.match(ip_pattern, value):
            raise ValueError("IP地址格式不正确")
        # 验证每个段是否在0-255范围内
        parts = value.split('.')
        for part in parts:
            if not 0 <= int(part) <= 255:
                raise ValueError("IP地址段必须在0-255范围内")
        return value


class NodeUpdateSchema(NodeCreateSchema):
    """节点更新模型"""
    ...


class NodeOutSchema(NodeCreateSchema, BaseSchema):
    """节点响应模型"""
    model_config = {"from_attributes": True}
    
    service_name: Optional[str] = Field(default=None, description="服务模块名称")


class TaskOutSchema(BaseSchema):
    """任务响应模型"""
    model_config = {"from_attributes": True}
    
    node_id: Optional[int] = Field(default=None, description="节点ID")
    ip: str = Field(..., description="任务IP地址")
    task_type: str = Field(..., description="任务类型(deploy:部署, restart:重启)")
    task_status: str = Field(..., description="任务状态(running:执行中, success:完成, failed:失败)")
    error_message: Optional[str] = Field(default=None, description="错误信息")


class NodeIdsSchema(BaseModel):
    """节点ID列表模型"""
    node_ids: List[int] = Field(..., description="节点ID列表", min_length=1)


# 更新前向引用
ServiceOutSchema.model_rebuild()
NodeOutSchema.model_rebuild()

