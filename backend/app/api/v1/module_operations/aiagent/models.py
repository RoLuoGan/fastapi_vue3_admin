# -*- coding: utf-8 -*-
"""
AI Agent 数据模型
定义 AI Agent 相关的数据库表结构
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import String, Integer, DateTime, Text, JSON, ForeignKey, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from app.core.base_model import CreatorMixin


class SessionStatus(str, enum.Enum):
    """会话状态枚举"""
    ACTIVE = "active"       # 活跃
    ENDED = "ended"         # 已结束
    ERROR = "error"         # 错误
    TAKEOVER = "takeover"   # 人工接管


class MessageRole(str, enum.Enum):
    """消息角色枚举"""
    USER = "user"           # 用户
    ASSISTANT = "assistant" # AI助手
    SYSTEM = "system"       # 系统
    TOOL = "tool"           # 工具


class OperationStatus(str, enum.Enum):
    """操作状态枚举"""
    PENDING = "pending"         # 待确认
    CONFIRMED = "confirmed"     # 已确认
    REJECTED = "rejected"       # 已拒绝
    SUCCESS = "success"         # 执行成功
    FAILED = "failed"           # 执行失败
    CANCELLED = "cancelled"     # 已取消


class RuleType(str, enum.Enum):
    """规则类型枚举"""
    PERMISSION = "permission"   # 权限规则
    ENVIRONMENT = "environment" # 环境规则
    BATCH = "batch"             # 批量规则
    TIME = "time"               # 时间窗口规则
    DEPENDENCY = "dependency"   # 依赖规则


class AIAgentSessionModel(CreatorMixin):
    """
    AI Agent 会话表
    
    存储用户与 AI Agent 的对话会话信息
    """
    __tablename__ = "operations_aiagent_session"
    __table_args__ = ({'comment': 'AI Agent会话表'})
    __loader_options__ = ["creator"]

    # 继承自 CreatorMixin: id, description, created_at, updated_at, creator_id, creator
    
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("system_users.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
        index=True,
        comment="用户ID"
    )
    session_name: Mapped[str] = mapped_column(String(200), nullable=False, comment='会话名称')
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=SessionStatus.ACTIVE.value,
        comment='会话状态'
    )
    context: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True, comment='会话上下文(JSON)')
    llm_model: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, comment='使用的LLM模型')
    total_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment='总消耗Token数')
    ended_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, comment='结束时间')

    # 关联关系
    messages = relationship("AIAgentMessageModel", back_populates="session", cascade="all, delete-orphan")
    operation_logs = relationship("AIAgentOperationLogModel", back_populates="session", cascade="all, delete-orphan")


class AIAgentMessageModel(CreatorMixin):
    """
    AI Agent 消息表
    
    存储会话中的每条消息记录
    """
    __tablename__ = "operations_aiagent_message"
    __table_args__ = ({'comment': 'AI Agent消息表'})
    __loader_options__ = ["creator"]

    # 继承自 CreatorMixin: id, description, created_at, updated_at, creator_id, creator
    
    session_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("operations_aiagent_session.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
        index=True,
        comment="会话ID"
    )
    role: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment='消息角色'
    )
    content: Mapped[str] = mapped_column(Text, nullable=False, comment='消息内容')
    tool_calls: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True, comment='工具调用记录(JSON)')
    tool_call_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, comment='工具调用ID')
    tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment='消息Token数')

    # 关联关系
    session = relationship("AIAgentSessionModel", back_populates="messages")


class AIAgentOperationLogModel(CreatorMixin):
    """
    AI Agent 操作日志表
    
    记录所有运维操作的执行记录
    """
    __tablename__ = "operations_aiagent_operation_log"
    __table_args__ = ({'comment': 'AI Agent操作日志表'})
    __loader_options__ = ["creator"]

    # 继承自 CreatorMixin: id, description, created_at, updated_at, creator_id, creator
    
    session_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("operations_aiagent_session.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
        index=True,
        comment="会话ID"
    )
    operation_type: Mapped[str] = mapped_column(String(100), nullable=False, comment='操作类型')
    tool_name: Mapped[str] = mapped_column(String(100), nullable=False, comment='工具名称')
    target_resource: Mapped[Optional[str]] = mapped_column(String(500), nullable=True, comment='目标资源')
    params: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True, comment='操作参数(JSON)')
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=OperationStatus.PENDING.value,
        comment='执行状态'
    )
    result: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True, comment='执行结果(JSON)')
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment='错误信息')
    confirmed_by: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment='确认人ID')
    need_confirm: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, comment='是否需要确认')
    confirm_reason: Mapped[Optional[str]] = mapped_column(String(500), nullable=True, comment='需要确认的原因')
    executed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, comment='执行时间')
    confirmed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, comment='确认时间')

    # 关联关系
    session = relationship("AIAgentSessionModel", back_populates="operation_logs")


class AIAgentRuleModel(CreatorMixin):
    """
    AI Agent 规则表
    
    定义各种运维操作的安全规则
    """
    __tablename__ = "operations_aiagent_rule"
    __table_args__ = ({'comment': 'AI Agent规则表'})
    __loader_options__ = ["creator"]

    # 继承自 CreatorMixin: id, description, created_at, updated_at, creator_id, creator
    
    rule_name: Mapped[str] = mapped_column(String(100), nullable=False, comment='规则名称')
    rule_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment='规则类型'
    )
    rule_config: Mapped[dict] = mapped_column(JSON, nullable=False, comment='规则配置(JSON)')
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment='优先级(数字越大优先级越高)')
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, comment='是否启用')
