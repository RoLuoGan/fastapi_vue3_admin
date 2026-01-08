# -*- coding: utf-8 -*-
"""
脚本管理路由
"""

from typing import List
from fastapi import APIRouter, Depends, Body, Path
from fastapi.responses import JSONResponse
from redis.asyncio.client import Redis

from app.common.response import SuccessResponse
from app.core.router_class import OperationLogRoute
from app.core.dependencies import AuthPermission, redis_getter
from app.core.base_params import PaginationQueryParam
from app.core.logger import logger
from app.api.v1.module_system.auth.schema import AuthSchema

from .param import ScriptQueryParam
from .schema import ScriptCreateSchema, ScriptUpdateSchema, ScriptRunSchema
from .service import ScriptService

router = APIRouter(route_class=OperationLogRoute, prefix="/script", tags=["脚本管理"])


@router.get("/list", summary="获取脚本列表", description="获取所有脚本列表")
async def get_list_controller(
    search: ScriptQueryParam = Depends(),
    auth: AuthSchema = Depends(AuthPermission(["operations:script:query"], check_data_scope=False)),
) -> JSONResponse:
    search_dict = search.__dict__ if hasattr(search, "__dict__") else search
    result = await ScriptService.get_list_service(auth=auth, search=search_dict)
    return SuccessResponse(data=result, msg="查询脚本列表成功")


@router.get("/page", summary="分页查询脚本", description="分页查询脚本列表")
async def get_page_controller(
    page: PaginationQueryParam = Depends(),
    search: ScriptQueryParam = Depends(),
    auth: AuthSchema = Depends(AuthPermission(["operations:script:query"], check_data_scope=False)),
) -> JSONResponse:
    result = await ScriptService.get_page_service(
        auth=auth,
        page_no=page.page_no or 1,
        page_size=page.page_size or 10,
        search=search,
        order_by=page.order_by,
    )
    return SuccessResponse(data=result, msg="查询脚本列表成功")


@router.get("/detail/{id}", summary="获取脚本详情", description="获取脚本详情")
async def get_detail_controller(
    id: int = Path(..., description="脚本ID"),
    auth: AuthSchema = Depends(AuthPermission(["operations:script:query"], check_data_scope=False)),
) -> JSONResponse:
    result = await ScriptService.get_detail_service(auth=auth, id=id)
    return SuccessResponse(data=result, msg="查询脚本详情成功")


@router.post("/create", summary="创建脚本", description="创建脚本")
async def create_controller(
    data: ScriptCreateSchema,
    auth: AuthSchema = Depends(AuthPermission(["operations:script:create"])),
) -> JSONResponse:
    result = await ScriptService.create_service(auth=auth, data=data)
    logger.info(f"创建脚本成功: {data.name}")
    return SuccessResponse(data=result, msg="创建脚本成功")


@router.put("/update/{id}", summary="更新脚本", description="更新脚本")
async def update_controller(
    id: int = Path(..., description="脚本ID"),
    data: ScriptUpdateSchema = Body(...),
    auth: AuthSchema = Depends(AuthPermission(["operations:script:update"])),
) -> JSONResponse:
    result = await ScriptService.update_service(auth=auth, id=id, data=data)
    logger.info(f"更新脚本成功: {id}")
    return SuccessResponse(data=result, msg="更新脚本成功")


@router.delete("/delete", summary="删除脚本", description="删除脚本")
async def delete_controller(
    ids: List[int] = Body(..., description="脚本ID列表"),
    auth: AuthSchema = Depends(AuthPermission(["operations:script:delete"])),
) -> JSONResponse:
    await ScriptService.delete_service(auth=auth, ids=ids)
    logger.info(f"删除脚本成功: {ids}")
    return SuccessResponse(msg="删除脚本成功")


@router.post("/run", summary="运行脚本", description="运行脚本")
async def run_controller(
    data: ScriptRunSchema,
    redis: Redis = Depends(redis_getter),
    auth: AuthSchema = Depends(AuthPermission(["operations:script:run"])),
) -> JSONResponse:
    result = await ScriptService.run_script_service(auth=auth, data=data, redis=redis)
    logger.info(f"运行脚本成功: script_id={data.script_id}")
    return SuccessResponse(data=result, msg=result.get("message", "脚本执行任务已启动"))


