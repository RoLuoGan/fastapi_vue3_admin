# -*- coding: utf-8 -*-
"""
服务器（节点）领域 Schema 定义
"""

from typing import Optional, Dict, Any

from pydantic import BaseModel, Field, field_validator, model_validator

from app.core.base_schema import BaseSchema


class ServerCreateSchema(BaseModel):
    """服务器节点创建模型"""
    service_id: int = Field(..., ge=1, description="服务模块ID")
    ip: str = Field(..., max_length=50, description="节点IP地址")
    port: Optional[int] = Field(default=22, ge=1, le=65535, description="端口号")
    status: bool = Field(default=True, description="是否启用(True:启用 False:停用)")
    description: Optional[str] = Field(default=None, max_length=255, description="备注说明")

    @field_validator("ip")
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


class ServerUpdateSchema(ServerCreateSchema):
    """服务器节点更新模型"""
    ...


class ServerOutSchema(ServerCreateSchema, BaseSchema):
    """服务器节点响应模型"""
    model_config = {"from_attributes": True}

    service_name: Optional[str] = Field(default=None, description="服务模块名称")

    @model_validator(mode="before")
    @classmethod
    def fill_service_name(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        if values is None:
            return values
        if not isinstance(values, dict):
            attr_names = [
                "id",
                "service_id",
                "ip",
                "port",
                "status",
                "description",
                "created_at",
                "updated_at",
                "service",
            ]
            values = {name: getattr(values, name, None) for name in attr_names}
        service = values.get("service")
        if service and not values.get("service_name"):
            if isinstance(service, dict):
                values["service_name"] = service.get("name")
            else:
                values["service_name"] = getattr(service, "name", None)
        return values

