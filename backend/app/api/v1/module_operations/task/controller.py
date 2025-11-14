# -*- coding: utf-8 -*-
"""
任务路由
"""

from fastapi import APIRouter, Depends, Body, Path, Request
from fastapi.responses import JSONResponse, StreamingResponse

from app.common.response import SuccessResponse
from app.core.router_class import OperationLogRoute
from app.core.dependencies import AuthPermission, get_current_user_by_query
from app.core.base_params import PaginationQueryParam
from app.core.logger import logger
from app.api.v1.module_system.auth.schema import AuthSchema

from .param import TaskQueryParam
from .schema import TaskLogSchema, NodeIdsSchema  # noqa: F401  # 触发前向引用
from ..server.schema import ServerOutSchema  # noqa: F401
from ..service_module.schema import ServiceOutSchema  # noqa: F401
from .service import TaskService

router = APIRouter(route_class=OperationLogRoute, prefix="/node", tags=["任务管理"])


@router.post("/deploy", summary="部署服务", description="多样化服务部署（模拟）")
async def deploy_controller(
    data: NodeIdsSchema,
    auth: AuthSchema = Depends(AuthPermission(["operations:node:deploy"])),
) -> JSONResponse:
    node_ids = data.node_ids
    result = await TaskService.deploy_service(node_ids=node_ids, auth=auth)
    logger.info(f"部署服务成功: {result}")
    return SuccessResponse(data=result, msg="部署任务已启动")


@router.post("/restart", summary="重启服务", description="重启服务（模拟）")
async def restart_controller(
    data: NodeIdsSchema,
    auth: AuthSchema = Depends(AuthPermission(["operations:node:restart"])),
) -> JSONResponse:
    node_ids = data.node_ids
    result = await TaskService.restart_service(node_ids=node_ids, auth=auth)
    logger.info(f"重启服务成功: {result}")
    return SuccessResponse(data=result, msg="重启任务已启动")


@router.get("/task/recent", summary="查询最近任务", description="查询最近20个任务")
async def get_recent_tasks_controller(
    limit: int = 20,
    auth: AuthSchema = Depends(AuthPermission(["operations:node:query"])),
) -> JSONResponse:
    result = await TaskService.get_recent_tasks_service(limit=limit, auth=auth)
    logger.info("查询最近任务成功")
    return SuccessResponse(data=result, msg="查询最近任务成功")


@router.get("/task/page", summary="分页查询任务", description="分页查询任务列表")
async def get_task_page_controller(
    page: PaginationQueryParam = Depends(),
    search: TaskQueryParam = Depends(),
    auth: AuthSchema = Depends(AuthPermission(["operations:task:query"])),
) -> JSONResponse:
    result = await TaskService.get_task_page_service(
        auth=auth,
        page_no=page.page_no or 1,
        page_size=page.page_size or 10,
        search=search,
        order_by=page.order_by,
    )
    logger.info("分页查询任务成功")
    return SuccessResponse(data=result, msg="查询任务列表成功")


@router.get("/task/detail/{id}", summary="查询任务详情", description="查询任务详情")
async def get_task_detail_controller(
    id: int = Path(..., description="任务ID"),
    auth: AuthSchema = Depends(AuthPermission(["operations:task:query"])),
) -> JSONResponse:
    result = await TaskService.get_task_detail_service(auth=auth, task_id=id)
    logger.info(f"查询任务详情成功 {id}")
    return SuccessResponse(data=result, msg="查询任务详情成功")


@router.get("/task/log/{id}", summary="查询任务日志", description="查询任务日志全文")
async def get_task_log_controller(
    id: int = Path(..., description="任务ID"),
    auth: AuthSchema = Depends(AuthPermission(["operations:task:log"])),
) -> JSONResponse:
    result = await TaskService.get_task_log_service(auth=auth, task_id=id)
    logger.info(f"查询任务日志成功 {id}")
    return SuccessResponse(data=result, msg="查询任务日志成功")


@router.delete("/task/delete", summary="删除任务", description="删除任务记录及日志")
async def delete_task_controller(
    ids: list[int] = Body(..., description="任务ID列表"),
    auth: AuthSchema = Depends(AuthPermission(["operations:task:delete"])),
) -> JSONResponse:
    await TaskService.delete_task_service(auth=auth, ids=ids)
    logger.info(f"删除任务成功 {ids}")
    return SuccessResponse(msg="删除任务成功")


@router.get("/task/{task_id}/stream", summary="任务日志流", description="任务日志SSE流")
async def stream_task_log_controller(
    request: Request,
    task_id: int = Path(..., description="任务ID"),
    auth: AuthSchema = Depends(get_current_user_by_query),
) -> StreamingResponse:
    permission_checker = AuthPermission(["operations:task:log"], check_data_scope=False)
    auth = await permission_checker(auth)
    last_event_id = (
        request.headers.get("last-event-id")
        or request.query_params.get("last_event_id")
        or request.query_params.get("lastEventId")
    )
    # stream_task_log_service 返回 AsyncGenerator，await 获取生成器
    # 生成器已经返回字节格式，直接使用
    generator = await TaskService.stream_task_log_service(
        auth=auth,
        task_id=task_id,
        last_event_id=last_event_id,
    )
    
    return StreamingResponse(
        generator,
        media_type="text/event-stream; charset=utf-8",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # 禁用nginx缓冲
            "Content-Encoding": "identity",  # 禁用压缩，确保实时推送
        },
    )

