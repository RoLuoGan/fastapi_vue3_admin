# -*- coding: utf-8 -*-
"""
任务领域 Schema 定义
"""

from typing import Optional, Dict, Any, TYPE_CHECKING, List
import json

from pydantic import BaseModel, Field, model_validator

from app.core.base_schema import BaseSchema

if TYPE_CHECKING:
    from ..server.schema import ServerOutSchema
    from ..service_module.schema import ServiceOutSchema


class TaskOutSchema(BaseSchema):
    """任务响应模型"""
    model_config = {"from_attributes": True}

    service_id: Optional[int] = Field(default=None, description="服务模块ID")
    service_name: Optional[str] = Field(default=None, description="服务模块名称")
    node_id: Optional[int] = Field(default=None, description="节点ID")
    node_name: Optional[str] = Field(default=None, description="节点名称")
    ip: str = Field(..., description="任务IP地址")
    task_type: str = Field(..., description="任务类型(deploy:部署, restart:重启)")
    task_status: str = Field(..., description="任务状态(running:执行中, success:完成, failed:失败)")
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

        if not isinstance(values, dict):
            attr_names = [
                "id",
                "service_id",
                "node_id",
                "ip",
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
                "service",
                "node",
            ]
            values = {name: getattr(values, name, None) for name in attr_names}

        params = values.get("params")
        if isinstance(params, str) and params:
            try:
                values["params"] = json.loads(params)
            except json.JSONDecodeError:
                values["params"] = {"raw": params}
        if not values.get("service_name"):
            service = values.get("service")
            if service:
                if isinstance(service, dict):
                    values["service_name"] = service.get("name")
                else:
                    values["service_name"] = getattr(service, "name", None)
        if not values.get("node_name"):
            node = values.get("node")
            if node:
                if isinstance(node, dict):
                    values["node_name"] = node.get("ip") or node.get("description")
                else:
                    values["node_name"] = getattr(node, "ip", None)
        return values


class TaskDetailSchema(TaskOutSchema):
    """任务详情响应模型"""
    node: Optional["ServerOutSchema"] = Field(default=None, description="节点信息")
    service: Optional["ServiceOutSchema"] = Field(default=None, description="服务模块信息")
    log_size: Optional[int] = Field(default=None, description="日志文件大小（字节）")


class TaskLogSchema(BaseModel):
    """任务日志内容响应模型"""
    content: str = Field(default="", description="日志内容")


class ExecuteTaskSchema(BaseModel):
    """执行任务模型"""
    node_ids: List[int] = Field(..., description="节点ID列表", min_length=1)
    task_type: str = Field(..., description="任务类型: deploy(部署) 或 restart(重启)", pattern="^(deploy|restart)$")


from ..server.schema import ServerOutSchema  # noqa: E402  # 解决前向引用
from ..service_module.schema import ServiceOutSchema  # noqa: E402

TaskDetailSchema.model_rebuild()

