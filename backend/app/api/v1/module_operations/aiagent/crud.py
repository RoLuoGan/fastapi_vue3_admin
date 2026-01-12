# -*- coding: utf-8 -*-
"""
AI Agent CRUD操作
数据库操作层
"""

from typing import List, Optional, Dict, Any
from datetime import datetime

from sqlalchemy import select, update, delete, desc, and_
from sqlalchemy.orm import selectinload

from app.api.v1.module_system.auth.schema import AuthSchema

from .models import (
    AIAgentSessionModel,
    AIAgentMessageModel,
    AIAgentOperationLogModel,
    AIAgentRuleModel,
    SessionStatus,
    MessageRole,
    OperationStatus,
    RuleType
)


class AIAgentCRUD:
    """AI Agent CRUD操作类"""
    
    def __init__(self, auth: AuthSchema):
        """初始化CRUD操作类"""
        self.auth = auth
        self.db = auth.db if auth else None
    
    # ==================== 会话操作 ====================
    
    async def create_session(
        self,
        user_id: int,
        session_name: str,
        llm_model: str = "deepseek"
    ) -> AIAgentSessionModel:
        """创建会话"""
        session = AIAgentSessionModel(
            user_id=user_id,
            session_name=session_name,
            status=SessionStatus.ACTIVE.value,
            llm_model=llm_model,
            context={}
        )
        self.db.add(session)
        await self.db.flush()
        await self.db.refresh(session)
        return session
    
    async def get_session(self, session_id: int) -> Optional[AIAgentSessionModel]:
        """获取会话"""
        result = await self.db.execute(
            select(AIAgentSessionModel).where(AIAgentSessionModel.id == session_id)
        )
        return result.scalar_one_or_none()
    
    async def update_session(
        self,
        session_id: int,
        **kwargs
    ) -> AIAgentSessionModel:
        """更新会话"""
        await self.db.execute(
            update(AIAgentSessionModel)
            .where(AIAgentSessionModel.id == session_id)
            .values(**kwargs)
        )
        await self.db.flush()
        return await self.get_session(session_id)
    
    async def get_user_sessions(
        self,
        user_id: int,
        limit: int = 20,
        offset: int = 0
    ) -> List[AIAgentSessionModel]:
        """获取用户的会话列表"""
        result = await self.db.execute(
            select(AIAgentSessionModel)
            .where(AIAgentSessionModel.user_id == user_id)
            .order_by(desc(AIAgentSessionModel.updated_at))
            .limit(limit)
            .offset(offset)
        )
        return result.scalars().all()
    
    async def end_session(self, session_id: int) -> AIAgentSessionModel:
        """结束会话"""
        return await self.update_session(
            session_id,
            status=SessionStatus.ENDED.value,
            ended_at=datetime.now()
        )
    
    # ==================== 消息操作 ====================
    
    async def create_message(
        self,
        session_id: int,
        role: MessageRole,
        content: str,
        tool_calls: Optional[Dict] = None,
        tool_call_id: Optional[str] = None,
        tokens: int = 0
    ) -> AIAgentMessageModel:
        """创建消息"""
        role_value = role.value if isinstance(role, MessageRole) else role
        message = AIAgentMessageModel(
            session_id=session_id,
            role=role_value,
            content=content,
            tool_calls=tool_calls,
            tool_call_id=tool_call_id,
            tokens=tokens
        )
        self.db.add(message)
        await self.db.flush()
        await self.db.refresh(message)
        return message
    
    async def get_session_history(
        self,
        session_id: int,
        limit: int = 50
    ) -> List[AIAgentMessageModel]:
        """获取会话历史消息"""
        result = await self.db.execute(
            select(AIAgentMessageModel)
            .where(AIAgentMessageModel.session_id == session_id)
            .order_by(AIAgentMessageModel.created_at)
            .limit(limit)
        )
        return result.scalars().all()
    
    # ==================== 操作日志 ====================
    
    async def create_operation_log(
        self,
        session_id: int,
        operation_type: str,
        tool_name: str,
        target_resource: Optional[str] = None,
        params: Optional[Dict] = None,
        need_confirm: bool = False,
        confirm_reason: Optional[str] = None,
        status: OperationStatus = OperationStatus.PENDING
    ) -> AIAgentOperationLogModel:
        """创建操作日志"""
        status_value = status.value if isinstance(status, OperationStatus) else status
        log = AIAgentOperationLogModel(
            session_id=session_id,
            operation_type=operation_type,
            tool_name=tool_name,
            target_resource=target_resource,
            params=params,
            need_confirm=need_confirm,
            confirm_reason=confirm_reason,
            status=status_value
        )
        self.db.add(log)
        await self.db.flush()
        await self.db.refresh(log)
        return log
    
    async def get_operation_log(self, log_id: int) -> Optional[AIAgentOperationLogModel]:
        """获取操作日志"""
        result = await self.db.execute(
            select(AIAgentOperationLogModel)
            .where(AIAgentOperationLogModel.id == log_id)
        )
        return result.scalar_one_or_none()
    
    async def update_operation_log(
        self,
        log_id: int,
        **kwargs
    ) -> AIAgentOperationLogModel:
        """更新操作日志"""
        await self.db.execute(
            update(AIAgentOperationLogModel)
            .where(AIAgentOperationLogModel.id == log_id)
            .values(**kwargs)
        )
        await self.db.flush()
        return await self.get_operation_log(log_id)
    
    async def get_pending_operations(
        self,
        session_id: Optional[int] = None
    ) -> List[AIAgentOperationLogModel]:
        """获取待确认的操作列表"""
        query = select(AIAgentOperationLogModel).where(
            AIAgentOperationLogModel.status == OperationStatus.PENDING.value
        )
        
        if session_id:
            query = query.where(AIAgentOperationLogModel.session_id == session_id)
        
        query = query.order_by(AIAgentOperationLogModel.created_at)
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    # ==================== 规则操作 ====================
    
    async def create_rule(
        self,
        rule_name: str,
        rule_type: RuleType,
        rule_config: Dict[str, Any],
        priority: int = 0,
        enabled: bool = True,
        description: Optional[str] = None
    ) -> AIAgentRuleModel:
        """创建规则"""
        rule_type_value = rule_type.value if isinstance(rule_type, RuleType) else rule_type
        rule = AIAgentRuleModel(
            rule_name=rule_name,
            rule_type=rule_type_value,
            rule_config=rule_config,
            priority=priority,
            enabled=enabled,
            description=description
        )
        self.db.add(rule)
        await self.db.flush()
        await self.db.refresh(rule)
        return rule
    
    async def get_rule(self, rule_id: int) -> Optional[AIAgentRuleModel]:
        """获取规则"""
        result = await self.db.execute(
            select(AIAgentRuleModel).where(AIAgentRuleModel.id == rule_id)
        )
        return result.scalar_one_or_none()
    
    async def get_enabled_rules(self) -> List[AIAgentRuleModel]:
        """获取所有启用的规则"""
        result = await self.db.execute(
            select(AIAgentRuleModel)
            .where(AIAgentRuleModel.enabled == True)
            .order_by(desc(AIAgentRuleModel.priority))
        )
        return result.scalars().all()
    
    async def update_rule(
        self,
        rule_id: int,
        **kwargs
    ) -> AIAgentRuleModel:
        """更新规则"""
        await self.db.execute(
            update(AIAgentRuleModel)
            .where(AIAgentRuleModel.id == rule_id)
            .values(**kwargs)
        )
        await self.db.flush()
        return await self.get_rule(rule_id)
    
    async def delete_rule(self, rule_id: int) -> bool:
        """删除规则"""
        await self.db.execute(
            delete(AIAgentRuleModel).where(AIAgentRuleModel.id == rule_id)
        )
        await self.db.flush()
        return True
    
    async def get_all_rules(
        self,
        limit: int = 50,
        offset: int = 0
    ) -> List[AIAgentRuleModel]:
        """获取所有规则"""
        result = await self.db.execute(
            select(AIAgentRuleModel)
            .order_by(desc(AIAgentRuleModel.priority))
            .limit(limit)
            .offset(offset)
        )
        return result.scalars().all()
