# -*- coding: utf-8 -*-
"""
脚本管理 Schema 定义
"""

from typing import Optional, Dict, Any, List
from enum import Enum
import json

from pydantic import BaseModel, Field, field_validator, model_validator

from app.core.base_schema import BaseSchema


class ScriptType(str, Enum):
    """脚本类型枚举"""
    PYTHON = "python"
    SHELL = "shell"

    @classmethod
    def get_label(cls, script_type: str) -> str:
        labels = {
            cls.PYTHON: "Python",
            cls.SHELL: "Shell",
        }
        return labels.get(script_type, script_type)


class ContentType(str, Enum):
    """脚本内容类型枚举"""
    TEXT = "text"
    LOCAL_PATH = "local_path"

    @classmethod
    def get_label(cls, content_type: str) -> str:
        labels = {
            cls.TEXT: "文本内容",
            cls.LOCAL_PATH: "本地路径",
        }
        return labels.get(content_type, content_type)


class ParamType(str, Enum):
    """参数类型枚举"""
    STRING = "string"
    INT = "int"
    FLOAT = "float"
    BOOL = "bool"
    LIST = "list"
    DICT = "dict"


class ScriptParamSchema(BaseModel):
    """脚本参数定义"""
    name: str = Field(..., max_length=50, description="参数名称")
    param_type: ParamType = Field(..., description="参数类型")
    required: bool = Field(default=True, description="是否必填")
    default: Optional[Any] = Field(default=None, description="默认值")
    description: Optional[str] = Field(default=None, max_length=255, description="参数描述")


class ScriptCreateSchema(BaseModel):
    """脚本创建模型"""
    name: str = Field(..., max_length=100, description="脚本名称")
    script_type: ScriptType = Field(..., description="脚本类型(python/shell)")
    content_type: ContentType = Field(default=ContentType.TEXT, description="脚本内容类型(text/local_path)")
    content: str = Field(..., description="脚本内容或本地路径")
    default_timeout: int = Field(default=3600, ge=60, le=86400, description="默认超时时间(秒)")
    queue_code: Optional[str] = Field(default=None, max_length=50, description="执行队列编码")
    params_schema: Optional[List[ScriptParamSchema]] = Field(default=None, description="脚本参数定义列表")
    status: bool = Field(default=True, description="是否启用")

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        if not value or len(value.strip()) == 0:
            raise ValueError("脚本名称不能为空")
        return value.strip()


class ScriptUpdateSchema(ScriptCreateSchema):
    """脚本更新模型"""
    ...


class ScriptOutSchema(BaseSchema):
    """脚本响应模型"""
    model_config = {"from_attributes": True}

    name: str = Field(..., description="脚本名称")
    script_type: str = Field(..., description="脚本类型")
    content_type: str = Field(..., description="脚本内容类型")
    content: str = Field(..., description="脚本内容或本地路径")
    default_timeout: int = Field(..., description="默认超时时间(秒)")
    queue_code: Optional[str] = Field(default=None, description="执行队列编码")
    params_schema: Optional[List[Dict[str, Any]]] = Field(default=None, description="脚本参数定义")
    status: bool = Field(..., description="是否启用")

    @model_validator(mode="before")
    @classmethod
    def parse_params_schema(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        if values is None:
            return values

        # 如果是ORM对象，转换为字典
        if not isinstance(values, dict):
            attr_names = [
                "id", "name", "script_type", "content_type", "content",
                "default_timeout", "queue_code", "params_schema", "status",
                "created_at", "updated_at", "description"
            ]
            values = {name: getattr(values, name, None) for name in attr_names}

        # 解析 JSON 格式的 params_schema 字段
        params_schema = values.get("params_schema")
        if isinstance(params_schema, str) and params_schema:
            try:
                values["params_schema"] = json.loads(params_schema)
            except json.JSONDecodeError:
                values["params_schema"] = None

        return values


class ScriptRunSchema(BaseModel):
    """运行脚本请求模型"""
    script_id: int = Field(..., ge=1, description="脚本ID")
    params: Optional[Dict[str, Any]] = Field(default=None, description="运行参数")
    timeout: Optional[int] = Field(default=None, ge=60, le=86400, description="超时时间(秒)，不传则使用脚本默认超时")
    target_nodes: Optional[List[str]] = Field(default=None, description="目标节点IP列表（可选，用于指定执行节点）")


