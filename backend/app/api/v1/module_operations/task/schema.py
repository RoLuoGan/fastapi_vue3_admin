# -*- coding: utf-8 -*-
"""
任务领域 Schema 定义
"""

from typing import Optional, Dict, Any, List
import json

from pydantic import BaseModel, Field, model_validator

from app.core.base_schema import BaseSchema


class TaskOutSchema(BaseSchema):
    """任务响应模型"""
    model_config = {"from_attributes": True}

    task_type: str = Field(..., description="任务类型(deploy:部署, restart:重启)")
    task_status: str = Field(..., description="任务状态(running:执行中, success:完成, failed:失败, partial_success:部分成功)")
    progress: int = Field(default=0, ge=0, le=100, description="任务进度百分比")
    log_path: Optional[str] = Field(default=None, description="任务日志路径")
    params: Optional[Dict[str, Any]] = Field(default=None, description="任务参数")
    error_message: Optional[str] = Field(default=None, description="错误信息")
    project: Optional[str] = Field(default=None, description="运维管理项目")
    idc: Optional[str] = Field(default=None, description="机房")
    module_group: Optional[str] = Field(default=None, description="模块分组")

    @model_validator(mode="before")
    @classmethod
    def parse_params(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        if values is None:
            return values

        # 如果是ORM对象，转换为字典
        if not isinstance(values, dict):
            attr_names = [
                "id",
                "task_type",
                "task_status",
                "progress",
                "log_path",
                "params",
                "error_message",
                "project",
                "idc",
                "module_group",
                "created_at",
                "updated_at",
            ]
            values = {name: getattr(values, name, None) for name in attr_names}

        # 解析 JSON 格式的 params 字段
        params = values.get("params")
        if isinstance(params, str) and params:
            try:
                values["params"] = json.loads(params)
            except json.JSONDecodeError:
                values["params"] = {"raw": params}
        
        return values


class TaskDetailSchema(TaskOutSchema):
    """任务详情响应模型"""
    log_size: Optional[int] = Field(default=None, description="日志文件大小（字节）")


class TaskLogSchema(BaseModel):
    """任务日志内容响应模型"""
    content: str = Field(default="", description="日志内容")


class OperatorMetaSchema(BaseModel):
    """操作元数据（支持任意结构，由客户端自定义）"""
    model_config = {"extra": "allow"}  # 允许额外字段
    
    def model_dump(self, **kwargs) -> Dict[str, Any]:
        """返回所有字段（包括额外字段）"""
        return super().model_dump(**kwargs)


class ExecuteTaskSchema(BaseModel):
    """执行任务模型（通用格式，支持多种任务类型）"""
    task_type: str = Field(..., description="任务类型: node_operator(节点操作), server_operator(服务器操作) 等")
    operator_type: str = Field(..., description="操作类型，由任务类型决定: deploy(部署), restart(重启), init(初始化) 等")
    operator_metas: List[Dict[str, Any]] = Field(..., description="操作元数据列表（任意结构，由客户端自定义）", min_length=1)
