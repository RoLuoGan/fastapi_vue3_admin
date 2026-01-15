# -*- coding: utf-8 -*-
"""
AI Agent 业务逻辑层
处理会话管理、消息处理、确认机制等业务逻辑
"""

import logging
from typing import Dict, Any, List, Optional, AsyncGenerator
from datetime import datetime

from app.config.setting import settings
from app.api.v1.module_system.auth.schema import AuthSchema
from app.core.exceptions import CustomException

from .crud import AIAgentCRUD
from .agent_core import AIAgent
from .confirm_handler import ConfirmHandler
from .rule_engine import RuleEngine
from .schema import (
    SessionCreateSchema,
    ChatRequest,
    ChatResponse,
    ToolConfirmRequest,
    TakeoverRequest
)
from .models import SessionStatus, MessageRole

logger = logging.getLogger(__name__)


class AIAgentService:
    """AI Agent业务服务类"""
    
    @classmethod
    async def create_session(
        cls,
        auth: AuthSchema,
        data: SessionCreateSchema
    ) -> Dict[str, Any]:
        """
        创建新会话
        
        Args:
            auth: 认证信息
            data: 会话创建数据
            
        Returns:
            会话信息
        """
        crud = AIAgentCRUD(auth)
        
        # 生成会话名称（如果未指定）
        session_name = data.session_name or f"对话_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # 创建会话
        session = await crud.create_session(
            user_id=auth.user.id,
            session_name=session_name,
            llm_model=data.llm_model
        )
        
        logger.info(f"创建AI Agent会话: session_id={session.id}, user_id={auth.user.id}")
        
        return {
            "session_id": session.id,
            "session_name": session.session_name,
            "status": session.status,
            "llm_model": session.llm_model,
            "created_at": session.created_at.isoformat()
        }
    
    @classmethod
    async def chat(
        cls,
        auth: AuthSchema,
        request: ChatRequest
    ) -> Dict[str, Any]:
        """
        处理聊天请求（非流式）
        
        Args:
            auth: 认证信息
            request: 聊天请求
            
        Returns:
            聊天响应
        """
        crud = AIAgentCRUD(auth)
        
        # 检查会话是否存在
        session = await crud.get_session(request.session_id)
        if not session:
            raise CustomException(msg="会话不存在")
        
        if session.status != SessionStatus.ACTIVE.value:
            raise CustomException(msg=f"会话状态不正确: {session.status}")
        
        # 创建AI Agent（不传递MCP客户端，让Agent内部使用MultiServerMCPClient）
        agent = AIAgent(
            auth=auth,
            session_id=request.session_id,
            llm_model=session.llm_model
        )
        
        # 处理消息
        result = await agent.chat(request.message)
        
        return {
            "session_id": request.session_id,
            "message_id": result["message_id"],
            "content": result["content"],
            "role": MessageRole.ASSISTANT.value
        }
    
    @classmethod
    async def chat_stream(
        cls,
        auth: AuthSchema,
        request: ChatRequest,
        redis_client = None
    ) -> AsyncGenerator[str, None]:
        """
        处理聊天请求（流式）
        
        Args:
            auth: 认证信息
            request: 聊天请求
            
        Yields:
            SSE格式的流式响应
        """
        crud = AIAgentCRUD(auth)
        
        # 检查会话
        session = await crud.get_session(request.session_id)
        if not session:
            yield f"data: {{'type':'error','error':'会话不存在'}}\n\n"
            return
        
        if session.status != SessionStatus.ACTIVE.value:
            yield f"data: {{'type':'error','error':'会话状态不正确'}}\n\n"
            return

        # 创建AI Agent（不传递MCP客户端，让Agent内部使用MultiServerMCPClient）
        agent = AIAgent(
            auth=auth,
            session_id=request.session_id,
            llm_model=session.llm_model,
            redis_client=redis_client
        )
        
        # 流式处理
        async for chunk in agent.chat_stream(request.message):
            import json
            yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
    
    
    @classmethod
    async def takeover_session(
        cls,
        auth: AuthSchema,
        request: TakeoverRequest
    ) -> Dict[str, Any]:
        """
        人工接管会话
        
        Args:
            auth: 认证信息
            request: 接管请求
            
        Returns:
            接管结果
        """
        crud = AIAgentCRUD(auth)
        
        # 检查会话
        session = await crud.get_session(request.session_id)
        if not session:
            raise CustomException(msg="会话不存在")
        
        # 检查权限
        # TODO: 添加管理员权限检查
        
        # 更新会话状态
        await crud.update_session(
            request.session_id,
            status=SessionStatus.TAKEOVER.value
        )
        
        # 记录接管消息
        await crud.create_message(
            session_id=request.session_id,
            role=MessageRole.SYSTEM,
            content=f"会话已被人工接管。原因：{request.reason or '无'}"
        )
        
        logger.info(f"会话被接管: session_id={request.session_id}, by={auth.user.username if auth.user else 'unknown'}")
        
        return {
            "session_id": request.session_id,
            "status": SessionStatus.TAKEOVER.value,
            "message": "会话已被人工接管"
        }
    
    @classmethod
    async def get_session_history(
        cls,
        auth: AuthSchema,
        session_id: int
    ) -> Dict[str, Any]:
        """
        获取会话历史
        
        Args:
            auth: 认证信息
            session_id: 会话ID
            
        Returns:
            会话历史
        """
        crud = AIAgentCRUD(auth)
        
        # 检查会话
        session = await crud.get_session(session_id)
        if not session:
            raise CustomException(msg="会话不存在")
        
        # 检查权限
        if session.user_id != auth.user.id:
            raise CustomException(msg="无权查看该会话")
        
        # 获取消息历史
        messages = await crud.get_session_history(session_id, limit=100)
        
        return {
            "session": {
                "id": session.id,
                "session_name": session.session_name,
                "status": session.status,
                "created_at": session.created_at.isoformat(),
                "updated_at": session.updated_at.isoformat()
            },
            "messages": [
                {
                    "id": msg.id,
                    "role": msg.role,
                    "content": msg.content,
                    "created_at": msg.created_at.isoformat(),
                    "tool_calls": msg.tool_calls
                }
                for msg in messages
            ],
            "total_messages": len(messages)
        }
    
    @classmethod
    async def get_user_sessions(
        cls,
        auth: AuthSchema,
        page: int = 1,
        page_size: int = 20
    ) -> Dict[str, Any]:
        """
        获取用户的会话列表
        
        Args:
            auth: 认证信息
            page: 页码
            page_size: 每页数量
            
        Returns:
            会话列表
        """
        crud = AIAgentCRUD(auth)
        
        offset = (page - 1) * page_size
        sessions = await crud.get_user_sessions(
            user_id=auth.user.id,
            limit=page_size,
            offset=offset
        )
        
        return {
            "sessions": [
                {
                    "id": s.id,
                    "session_name": s.session_name,
                    "status": s.status,
                    "llm_model": s.llm_model,
                    "total_tokens": s.total_tokens,
                    "created_at": s.created_at.isoformat(),
                    "updated_at": s.updated_at.isoformat()
                }
                for s in sessions
            ],
            "page": page,
            "page_size": page_size
        }
    
    @classmethod
    async def end_session(
        cls,
        auth: AuthSchema,
        session_id: int
    ) -> Dict[str, Any]:
        """
        结束会话
        
        Args:
            auth: 认证信息
            session_id: 会话ID
            
        Returns:
            结果
        """
        crud = AIAgentCRUD(auth)
        
        # 检查会话
        session = await crud.get_session(session_id)
        if not session:
            raise CustomException(msg="会话不存在")
        
        # 检查权限
        if session.user_id != auth.user.id:
            raise CustomException(msg="无权结束该会话")
        
        # 结束会话
        await crud.end_session(session_id)
        
        return {
            "session_id": session_id,
            "status": SessionStatus.ENDED.value,
            "message": "会话已结束"
        }
    

    @classmethod
    async def confirm_tool_call(
        cls,
        auth: AuthSchema,
        operation_id: int,
        request: ToolConfirmRequest
    ) -> Dict[str, Any]:
        """
        确认或拒绝MCP工具调用

        Args:
            auth: 认证信息
            operation_id: 操作ID
            request: 确认请求

        Returns:
            执行结果
        """
        logger.info(f"[confirm_tool_call] 开始处理确认请求: operation_id={operation_id}, confirmed={request.confirmed}, user_id={auth.user.id}")

        crud = AIAgentCRUD(auth)

        # 获取操作日志
        operation_log = await crud.get_operation_log(operation_id)
        if not operation_log:
            raise CustomException(msg="操作不存在或已过期")

        # 检查权限（只能确认自己会话的操作）
        session = await crud.get_session(operation_log.session_id)
        if session.user_id != auth.user.id:
            raise CustomException(msg="无权确认该操作")

        # 检查操作状态
        if operation_log.status != "pending":
            if operation_log.status == "confirmed":
                return {
                    "operation_id": operation_id,
                    "success": True,
                    "result": "操作已被确认并执行",
                    "confirmed": True
                }
            elif operation_log.status == "rejected":
                return {
                    "operation_id": operation_id,
                    "success": False,
                    "result": "操作已被拒绝",
                    "confirmed": False
                }
            else:
                return {
                    "operation_id": operation_id,
                    "success": False,
                    "result": f"操作状态异常: {operation_log.status}",
                    "confirmed": False
                }

        # 创建AI Agent来执行确认
        agent = AIAgent(
            auth=auth,
            session_id=operation_log.session_id,
            llm_model=session.llm_model
        )

        # 执行确认
        result = await agent.confirm_and_execute_tool(operation_id, request.confirmed)

        return {
            "operation_id": operation_id,
            "success": "❌" not in result and "失败" not in result,
            "result": result,
            "confirmed": request.confirmed
        }
