# -*- coding: utf-8 -*-
"""
服务器（节点）领域 Schema 定义
"""

from typing import Optional, Dict, Any, List

from pydantic import BaseModel, Field, field_validator, model_validator

from app.core.base_schema import BaseSchema


class ServerCreateSchema(BaseModel):
    """服务器节点创建模型"""
    service_id: Optional[int] = Field(default=None, ge=1, description="服务模块ID")
    ip: str = Field(..., max_length=50, description="节点IP地址")
    port: Optional[int] = Field(default=22, ge=1, le=65535, description="端口号")
    status: bool = Field(default=True, description="是否启用(True:启用 False:停用)")
    description: Optional[str] = Field(default=None, max_length=255, description="备注说明")
    project: Optional[str] = Field(default=None, max_length=50, description="运维管理项目")
    idc: Optional[str] = Field(default=None, max_length=50, description="机房")
    tags: Optional[str] = Field(default=None, max_length=100, description="服务器标签")
    service_ids: Optional[List[int]] = Field(default=None, description="关联的服务模块ID列表（仅用于更新关联关系）")

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
    services: Optional[List[Dict[str, Any]]] = Field(default=None, description="关联的服务模块列表")

    @model_validator(mode="before")
    @classmethod
    def fill_service_info(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        from sqlalchemy.inspection import inspect as sa_inspect
        
        if values is None:
            return values
        if not isinstance(values, dict):
            # 基本属性（不触发懒加载）
            basic_attrs = [
                "id",
                "service_id",
                "ip",
                "port",
                "status",
                "description",
                "project",
                "idc",
                "tags",
                "created_at",
                "updated_at",
            ]
            values_dict = {name: getattr(values, name, None) for name in basic_attrs}
            
            # 安全地获取关联属性（仅当已加载时）
            try:
                # 检查对象是否有 inspect state
                state = sa_inspect(values)
                
                # 检查 service 是否已加载
                if "service" not in state.unloaded:
                    values_dict["service"] = getattr(values, "service", None)
                else:
                    values_dict["service"] = None
                
                # 检查 services 是否已加载
                if "services" not in state.unloaded:
                    values_dict["services"] = getattr(values, "services", None)
                else:
                    values_dict["services"] = None
            except:
                # 如果检查失败，使用 __dict__ 获取已加载的属性
                if hasattr(values, "__dict__"):
                    values_dict["service"] = values.__dict__.get("service", None)
                    values_dict["services"] = values.__dict__.get("services", None)
            
            values = values_dict
        
        # 填充单一service_name（向后兼容）
        service = values.get("service")
        if service and not values.get("service_name"):
            if isinstance(service, dict):
                values["service_name"] = service.get("name")
            else:
                values["service_name"] = getattr(service, "name", None)
        
        # 填充services列表
        services = values.get("services")
        if services:
            services_list = []
            for svc in services:
                if isinstance(svc, dict):
                    services_list.append(svc)
                else:
                    services_list.append({
                        "id": getattr(svc, "id", None),
                        "name": getattr(svc, "name", None),
                        "code": getattr(svc, "code", None),
                        "status": getattr(svc, "status", None),
                        "project": getattr(svc, "project", None),
                        "module_group": getattr(svc, "module_group", None),
                    })
            values["services"] = services_list
        
        return values

