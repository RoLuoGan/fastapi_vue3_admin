# -*- coding: utf-8 -*-
"""
AI Agent Schema定义
定义请求和响应的数据模型
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


# ==================== 会话相关 ====================

class SessionCreateSchema(BaseModel):
    """创建会话请求"""
    session_name: Optional[str] = Field(None, description="会话名称，不指定则自动生成")
    llm_model: Optional[str] = Field("deepseek", description="使用的LLM模型")


class SessionOutSchema(BaseModel):
    """会话输出"""
    id: int
    user_id: int
    session_name: str
    status: str
    llm_model: Optional[str]
    total_tokens: int
    created_at: datetime
    updated_at: datetime
    ended_at: Optional[datetime]
    
    class Config:
        from_attributes = True


# ==================== 消息相关 ====================

class ChatRequest(BaseModel):
    """聊天请求"""
    session_id: int = Field(..., description="会话ID")
    message: str = Field(..., description="用户消息")
    stream: bool = Field(False, description="是否流式返回")


class ChatResponse(BaseModel):
    """聊天响应"""
    session_id: int
    message_id: int
    role: str
    content: str
    tool_calls: Optional[List[Dict[str, Any]]] = None
    tokens: int = 0


class StreamChunk(BaseModel):
    """流式响应块"""
    type: str = Field(..., description="消息类型: text/tool_call/complete/error/mcp_tool_confirm")
    content: Optional[str] = None
    tool_call: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    # 新增字段用于MCP工具确认
    operation_id: Optional[int] = None
    tool_name: Optional[str] = None
    tool_call_id: Optional[str] = None
    tool_args: Optional[Dict[str, Any]] = None
    confirm_reason: Optional[str] = None
    timestamp: Optional[str] = None


# ==================== 操作确认相关 ====================

class ToolConfirmRequest(BaseModel):
    """工具确认请求"""
    confirmed: bool = Field(..., description="是否确认执行")
    comment: Optional[str] = Field(None, description="确认备注")

    class Config:
        extra = "forbid"  # 禁止额外的字段


class OperationPendingNotification(BaseModel):
    """待确认操作通知"""
    operation_id: int
    operation_type: str
    tool_name: str
    target_resource: Optional[str]
    params: Dict[str, Any]
    confirm_reason: str
    timeout: int = Field(300, description="确认超时时间（秒）")


# ==================== 人工接管相关 ====================

class TakeoverRequest(BaseModel):
    """人工接管请求"""
    session_id: int = Field(..., description="会话ID")
    reason: Optional[str] = Field(None, description="接管原因")


class TakeoverResponse(BaseModel):
    """人工接管响应"""
    session_id: int
    status: str
    message: str


# ==================== 历史记录相关 ====================

class MessageOutSchema(BaseModel):
    """消息输出"""
    id: int
    session_id: int
    role: str
    content: str
    tool_calls: Optional[Dict[str, Any]]
    tokens: int
    created_at: datetime
    
    class Config:
        from_attributes = True


class SessionHistoryResponse(BaseModel):
    """会话历史响应"""
    session: SessionOutSchema
    messages: List[MessageOutSchema]
    total_messages: int


class SessionListResponse(BaseModel):
    """会话列表响应"""
    sessions: List[SessionOutSchema]
    total: int
    page: int
    page_size: int


# ==================== 规则相关 ====================

class RuleCreateSchema(BaseModel):
    """创建规则请求"""
    rule_name: str = Field(..., description="规则名称")
    rule_type: str = Field(..., description="规则类型")
    rule_config: Dict[str, Any] = Field(..., description="规则配置")
    priority: int = Field(0, description="优先级")
    enabled: bool = Field(True, description="是否启用")
    description: Optional[str] = Field(None, description="规则描述")


class RuleUpdateSchema(BaseModel):
    """更新规则请求"""
    rule_name: Optional[str] = None
    rule_config: Optional[Dict[str, Any]] = None
    priority: Optional[int] = None
    enabled: Optional[bool] = None
    description: Optional[str] = None


class RuleOutSchema(BaseModel):
    """规则输出"""
    id: int
    rule_name: str
    rule_type: str
    rule_config: Dict[str, Any]
    priority: int
    enabled: bool
    description: Optional[str]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
