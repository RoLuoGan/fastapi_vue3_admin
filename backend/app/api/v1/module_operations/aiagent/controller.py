# -*- coding: utf-8 -*-
"""
AI Agent 控制器
提供AI Agent相关的API接口
"""

from fastapi import APIRouter, Depends, Path, Body, Request
from fastapi.responses import JSONResponse, StreamingResponse
from typing import Optional

from app.common.response import SuccessResponse
from app.core.router_class import OperationLogRoute
from app.core.dependencies import AuthPermission
from app.core.logger import logger
from app.api.v1.module_system.auth.schema import AuthSchema

from .schema import (
    SessionCreateSchema,
    ChatRequest,
    OperationConfirmRequest,
    TakeoverRequest,
    RuleCreateSchema,
    RuleUpdateSchema
)
from .service import AIAgentService
from .crud import AIAgentCRUD

router = APIRouter(route_class=OperationLogRoute, prefix="/aiagent", tags=["运维AI助手"])


# ==================== 会话管理 ====================

@router.post("/session/create", summary="创建AI Agent会话")
async def create_session(
    data: SessionCreateSchema = Body(...),
    auth: AuthSchema = Depends(AuthPermission(["operations:aiagent:session"], check_data_scope=False)),
) -> JSONResponse:
    """创建新的AI Agent会话"""
    result = await AIAgentService.create_session(auth=auth, data=data)
    logger.info(f"创建AI Agent会话成功: session_id={result['session_id']}")
    return SuccessResponse(data=result, msg="创建会话成功")


@router.get("/session/list", summary="获取用户会话列表")
async def get_user_sessions(
    page: int = 1,
    page_size: int = 20,
    auth: AuthSchema = Depends(AuthPermission(["operations:aiagent:session"], check_data_scope=False)),
) -> JSONResponse:
    """获取当前用户的会话列表"""
    result = await AIAgentService.get_user_sessions(
        auth=auth,
        page=page,
        page_size=page_size
    )
    return SuccessResponse(data=result, msg="查询成功")


@router.get("/session/{session_id}/history", summary="获取会话历史")
async def get_session_history(
    session_id: int = Path(..., description="会话ID"),
    auth: AuthSchema = Depends(AuthPermission(["operations:aiagent:session"], check_data_scope=False)),
) -> JSONResponse:
    """获取指定会话的消息历史"""
    result = await AIAgentService.get_session_history(auth=auth, session_id=session_id)
    return SuccessResponse(data=result, msg="查询成功")


@router.post("/session/{session_id}/end", summary="结束会话")
async def end_session(
    session_id: int = Path(..., description="会话ID"),
    auth: AuthSchema = Depends(AuthPermission(["operations:aiagent:session"], check_data_scope=False)),
) -> JSONResponse:
    """结束指定会话"""
    result = await AIAgentService.end_session(auth=auth, session_id=session_id)
    return SuccessResponse(data=result, msg="会话已结束")


# ==================== 聊天接口 ====================

@router.post("/chat", summary="发送消息（非流式）")
async def chat(
    request: ChatRequest = Body(...),
    auth: AuthSchema = Depends(AuthPermission(["operations:aiagent:chat"], check_data_scope=False)),
) -> JSONResponse:
    """
    发送消息给AI Agent（非流式响应）
    
    请求体：
    - session_id: 会话ID
    - message: 用户消息
    """
    result = await AIAgentService.chat(auth=auth, request=request)
    return SuccessResponse(data=result, msg="消息发送成功")


@router.post("/chat/stream", summary="发送消息（流式）")
async def chat_stream(
    request: ChatRequest = Body(...),
    auth: AuthSchema = Depends(AuthPermission(["operations:aiagent:chat"], check_data_scope=False)),
):
    """
    发送消息给AI Agent（流式响应，SSE格式）
    
    返回Server-Sent Events流，前端需要使用EventSource接收
    """
    return StreamingResponse(
        AIAgentService.chat_stream(auth=auth, request=request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


# ==================== 操作确认 ====================

@router.get("/operations/pending", summary="获取待确认操作列表")
async def get_pending_operations(
    session_id: Optional[int] = None,
    auth: AuthSchema = Depends(AuthPermission(["operations:aiagent:confirm"], check_data_scope=False)),
) -> JSONResponse:
    """获取待确认的操作列表"""
    result = await AIAgentService.get_pending_operations(
        auth=auth,
        session_id=session_id
    )
    return SuccessResponse(data=result, msg="查询成功")


@router.post("/operation/{operation_id}/confirm", summary="确认操作")
async def confirm_operation(
    operation_id: int = Path(..., description="操作ID"),
    request: OperationConfirmRequest = Body(...),
    auth: AuthSchema = Depends(AuthPermission(["operations:aiagent:confirm"], check_data_scope=False)),
) -> JSONResponse:
    """
    确认或拒绝待确认的操作
    
    请求体：
    - confirmed: true表示确认，false表示拒绝
    - comment: 备注（可选）
    """
    # 更新请求中的operation_id
    request.operation_id = operation_id
    
    result = await AIAgentService.confirm_operation(auth=auth, request=request)
    
    if result.get("status") == "success":
        return SuccessResponse(data=result, msg="操作已确认并执行")
    else:
        return SuccessResponse(data=result, msg="操作已拒绝")


# ==================== 人工接管 ====================

@router.post("/session/{session_id}/takeover", summary="人工接管会话")
async def takeover_session(
    session_id: int = Path(..., description="会话ID"),
    request: TakeoverRequest = Body(...),
    auth: AuthSchema = Depends(AuthPermission(["operations:aiagent:takeover"], check_data_scope=False)),
) -> JSONResponse:
    """
    人工接管AI Agent会话（需要管理员权限）
    
    请求体：
    - reason: 接管原因（可选）
    """
    request.session_id = session_id
    result = await AIAgentService.takeover_session(auth=auth, request=request)
    logger.info(f"会话已被接管: session_id={session_id}, user={auth.user.username if auth.user else 'unknown'}")
    return SuccessResponse(data=result, msg="会话已被接管")


# ==================== 规则管理 ====================

@router.get("/rules", summary="获取规则列表")
async def get_rules(
    auth: AuthSchema = Depends(AuthPermission(["operations:aiagent:rule"], check_data_scope=False)),
) -> JSONResponse:
    """获取所有AI Agent规则"""
    crud = AIAgentCRUD(auth)
    rules = await crud.get_all_rules(limit=100)
    
    return SuccessResponse(
        data=[
            {
                "id": r.id,
                "rule_name": r.rule_name,
                "rule_type": r.rule_type,
                "rule_config": r.rule_config,
                "priority": r.priority,
                "enabled": r.enabled,
                "description": r.description,
                "created_at": r.created_at.isoformat(),
                "updated_at": r.updated_at.isoformat()
            }
            for r in rules
        ],
        msg="查询成功"
    )


@router.post("/rules/create", summary="创建规则")
async def create_rule(
    data: RuleCreateSchema = Body(...),
    auth: AuthSchema = Depends(AuthPermission(["operations:aiagent:rule"], check_data_scope=False)),
) -> JSONResponse:
    """创建新的AI Agent规则"""
    crud = AIAgentCRUD(auth)
    rule = await crud.create_rule(
        rule_name=data.rule_name,
        rule_type=data.rule_type,
        rule_config=data.rule_config,
        priority=data.priority,
        enabled=data.enabled,
        description=data.description
    )
    
    logger.info(f"创建规则成功: rule_id={rule.id}, name={rule.rule_name}")
    return SuccessResponse(data={"id": rule.id}, msg="创建成功")


@router.put("/rules/{rule_id}", summary="更新规则")
async def update_rule(
    rule_id: int = Path(..., description="规则ID"),
    data: RuleUpdateSchema = Body(...),
    auth: AuthSchema = Depends(AuthPermission(["operations:aiagent:rule"], check_data_scope=False)),
) -> JSONResponse:
    """更新AI Agent规则"""
    crud = AIAgentCRUD(auth)
    
    # 过滤None值
    update_data = {k: v for k, v in data.model_dump().items() if v is not None}
    
    await crud.update_rule(rule_id, **update_data)
    
    logger.info(f"更新规则成功: rule_id={rule_id}")
    return SuccessResponse(msg="更新成功")


@router.delete("/rules/{rule_id}", summary="删除规则")
async def delete_rule(
    rule_id: int = Path(..., description="规则ID"),
    auth: AuthSchema = Depends(AuthPermission(["operations:aiagent:rule"], check_data_scope=False)),
) -> JSONResponse:
    """删除AI Agent规则"""
    crud = AIAgentCRUD(auth)
    await crud.delete_rule(rule_id)
    
    logger.info(f"删除规则成功: rule_id={rule_id}")
    return SuccessResponse(msg="删除成功")
