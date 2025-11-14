# -*- coding: utf-8 -*-
"""
服务模块领域 Schema 定义
"""

from typing import Optional, List, TYPE_CHECKING

from pydantic import BaseModel, Field, field_validator

from app.core.base_schema import BaseSchema

if TYPE_CHECKING:
    from ..server.schema import ServerOutSchema

if TYPE_CHECKING:  # 仅用于类型提示，避免循环导入
    from ..server.schema import NodeOutSchema


class ServiceCreateSchema(BaseModel):
    """服务模块创建模型"""
    name: str = Field(..., max_length=100, description="服务模块名称")
    code: Optional[str] = Field(default=None, max_length=50, description="服务模块编码")
    status: bool = Field(default=True, description="是否启用(True:启用 False:停用)")
    description: Optional[str] = Field(default=None, max_length=255, description="备注说明")
    project: Optional[str] = Field(default=None, max_length=50, description="运维管理项目")
    module_group: Optional[str] = Field(default=None, max_length=50, description="模块分组")
    node_ids: Optional[List[int]] = Field(default=None, description="关联的节点ID列表")

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        if not value or len(value.strip()) == 0:
            raise ValueError("服务模块名称不能为空")
        return value.replace(" ", "")

    @field_validator("code")
    @classmethod
    def validate_code(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        v = value.strip()
        if v == "":
            return None
        import re
        if not re.match(r"^[A-Za-z][A-Za-z0-9_]*$", v):
            raise ValueError("服务模块编码必须以字母开头，且仅包含字母/数字/下划线")
        return v


class ServiceUpdateSchema(ServiceCreateSchema):
    """服务模块更新模型"""
    ...


class ServiceOutSchema(ServiceCreateSchema, BaseSchema):
    """服务模块响应模型"""
    model_config = {"from_attributes": True}

    nodes: Optional[List["ServerOutSchema"]] = Field(default=None, description="节点列表")


from ..server.schema import ServerOutSchema  # noqa: E402

ServiceOutSchema.model_rebuild()
