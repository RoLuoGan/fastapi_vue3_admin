# -*- coding: utf-8 -*-
"""
任务领域 Schema 定义
"""

from typing import Optional, Dict, Any, List
from enum import Enum
import json

from pydantic import BaseModel, Field, model_validator

from app.core.base_schema import BaseSchema


# ==================== 任务状态枚举 ====================

class TaskStatus(str, Enum):
    """任务状态枚举"""
    RUNNING = "running"  # 执行中
    SUCCESS = "success"  # 成功
    FAILED = "failed"  # 失败
    PARTIAL_SUCCESS = "partial_success"  # 部分成功
    CANCELLED = "cancelled"  # 已取消
    CANCELLING = "cancelling"  # 取消中
    
    @classmethod
    def get_label(cls, status: str) -> str:
        """获取状态标签"""
        labels = {
            cls.RUNNING: "执行中",
            cls.SUCCESS: "成功",
            cls.FAILED: "失败",
            cls.PARTIAL_SUCCESS: "部分成功",
            cls.CANCELLED: "已取消",
            cls.CANCELLING: "取消中",
        }
        return labels.get(status, status)
    
    @classmethod
    def is_finished(cls, status: str) -> bool:
        """判断任务是否已结束"""
        return status in (cls.SUCCESS, cls.FAILED, cls.PARTIAL_SUCCESS, cls.CANCELLED)
    
    @classmethod
    def is_running(cls, status: str) -> bool:
        """判断任务是否正在运行"""
        return status == cls.RUNNING


# ==================== 任务类型枚举 ====================

class TaskType(str, Enum):
    """任务类型枚举"""
    NODE_OPERATOR = "node_operator"  # 节点操作
    SERVER_OPERATOR = "server_operator"  # 服务器操作
    
    @classmethod
    def get_label(cls, task_type: str) -> str:
        """获取任务类型标签"""
        labels = {
            cls.NODE_OPERATOR: "节点操作",
            cls.SERVER_OPERATOR: "服务器操作",
        }
        return labels.get(task_type, task_type)


# ==================== 操作类型枚举 ====================

class OperatorType(str, Enum):
    """操作类型枚举"""
    DEPLOY = "deploy"  # 部署
    RESTART = "restart"  # 重启
    INIT = "init"  # 初始化
    START = "start"  # 启动
    STOP = "stop"  # 停止
    
    @classmethod
    def get_label(cls, operator_type: str) -> str:
        """获取操作类型标签"""
        labels = {
            cls.DEPLOY: "部署",
            cls.RESTART: "重启",
            cls.INIT: "初始化",
            cls.START: "启动",
            cls.STOP: "停止",
        }
        return labels.get(operator_type, operator_type)
    
    @classmethod
    def get_tag_type(cls, operator_type: str) -> str:
        """获取操作类型对应的标签类型（用于前端显示）"""
        tag_types = {
            cls.DEPLOY: "success",
            cls.RESTART: "warning",
            cls.INIT: "info",
            cls.START: "success",
            cls.STOP: "danger",
        }
        return tag_types.get(operator_type, "info")


class TaskOutSchema(BaseSchema):
    """任务响应模型"""
    model_config = {"from_attributes": True}

    task_type: str = Field(..., description=f"任务类型: {', '.join([f'{t.value}({TaskType.get_label(t.value)})' for t in TaskType])}")
    task_status: str = Field(..., description=f"任务状态: {', '.join([f'{s.value}({TaskStatus.get_label(s.value)})' for s in TaskStatus])}")
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
    task_type: str = Field(..., description=f"任务类型: {', '.join([f'{t.value}({TaskType.get_label(t.value)})' for t in TaskType])}")
    operator_type: str = Field(..., description=f"操作类型: {', '.join([f'{o.value}({OperatorType.get_label(o.value)})' for o in OperatorType])}")
    operator_metas: List[Dict[str, Any]] = Field(..., description="操作元数据列表（任意结构，由客户端自定义）", min_length=1)
