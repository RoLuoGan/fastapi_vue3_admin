# -*- coding: utf-8 -*-
"""
Celery Worker 节点路由
"""

from typing import List
from fastapi import APIRouter, Depends, Body, Path
from fastapi.responses import JSONResponse

from app.common.response import SuccessResponse
from app.core.router_class import OperationLogRoute
from app.core.dependencies import AuthPermission
from app.core.base_params import PaginationQueryParam
from app.core.logger import logger
from app.api.v1.module_system.auth.schema import AuthSchema

from .param import CeleryWorkerQueryParam
from .schema import CeleryWorkerCreateSchema, CeleryWorkerUpdateSchema, CeleryWorkerRegisterSchema
from .service import CeleryWorkerService

router = APIRouter(route_class=OperationLogRoute, prefix="/celery-worker", tags=["Celery Worker节点管理"])


@router.get("/list", summary="获取Worker列表", description="获取所有Worker节点列表")
async def get_list_controller(
    search: CeleryWorkerQueryParam = Depends(),
    auth: AuthSchema = Depends(AuthPermission(["operations:celery_worker:query"], check_data_scope=False)),
) -> JSONResponse:
    search_dict = search.__dict__ if hasattr(search, "__dict__") else search
    result = await CeleryWorkerService.get_list_service(auth=auth, search=search_dict)
    return SuccessResponse(data=result, msg="查询Worker列表成功")


@router.get("/page", summary="分页查询Worker", description="分页查询Worker节点列表")
async def get_page_controller(
    page: PaginationQueryParam = Depends(),
    search: CeleryWorkerQueryParam = Depends(),
    auth: AuthSchema = Depends(AuthPermission(["operations:celery_worker:query"], check_data_scope=False)),
) -> JSONResponse:
    result = await CeleryWorkerService.get_page_service(
        auth=auth,
        page_no=page.page_no or 1,
        page_size=page.page_size or 10,
        search=search,
        order_by=page.order_by,
    )
    return SuccessResponse(data=result, msg="查询Worker列表成功")


@router.get("/queues", summary="获取队列列表", description="获取所有执行队列列表（去重）")
async def get_queues_controller(
    auth: AuthSchema = Depends(AuthPermission(["operations:celery_worker:query"], check_data_scope=False)),
) -> JSONResponse:
    result = await CeleryWorkerService.get_queues_service(auth=auth)
    return SuccessResponse(data=result, msg="查询队列列表成功")


@router.get("/detail/{id}", summary="获取Worker详情", description="获取Worker节点详情")
async def get_detail_controller(
    id: int = Path(..., description="Worker ID"),
    auth: AuthSchema = Depends(AuthPermission(["operations:celery_worker:query"], check_data_scope=False)),
) -> JSONResponse:
    result = await CeleryWorkerService.get_detail_service(auth=auth, id=id)
    return SuccessResponse(data=result, msg="查询Worker详情成功")


@router.post("/create", summary="创建Worker", description="创建Worker节点")
async def create_controller(
    data: CeleryWorkerCreateSchema,
    auth: AuthSchema = Depends(AuthPermission(["operations:celery_worker:create"])),
) -> JSONResponse:
    result = await CeleryWorkerService.create_service(auth=auth, data=data)
    logger.info(f"创建Worker成功: {data.queue_code}@{data.node_ip}")
    return SuccessResponse(data=result, msg="创建Worker成功")


@router.put("/update/{id}", summary="更新Worker", description="更新Worker节点")
async def update_controller(
    id: int = Path(..., description="Worker ID"),
    data: CeleryWorkerUpdateSchema = Body(...),
    auth: AuthSchema = Depends(AuthPermission(["operations:celery_worker:update"])),
) -> JSONResponse:
    result = await CeleryWorkerService.update_service(auth=auth, id=id, data=data)
    logger.info(f"更新Worker成功: {id}")
    return SuccessResponse(data=result, msg="更新Worker成功")


@router.delete("/delete", summary="删除Worker", description="删除Worker节点")
async def delete_controller(
    ids: List[int] = Body(..., description="Worker ID列表"),
    auth: AuthSchema = Depends(AuthPermission(["operations:celery_worker:delete"])),
) -> JSONResponse:
    await CeleryWorkerService.delete_service(auth=auth, ids=ids)
    logger.info(f"删除Worker成功: {ids}")
    return SuccessResponse(msg="删除Worker成功")


@router.post("/register", summary="注册Worker", description="Worker节点自动注册/心跳（供Celery Worker调用）")
async def register_controller(
    data: CeleryWorkerRegisterSchema,
    auth: AuthSchema = Depends(AuthPermission(["operations:celery_worker:register"], check_data_scope=False)),
) -> JSONResponse:
    result = await CeleryWorkerService.register_service(
        auth=auth,
        queue_name=data.queue_name,
        queue_code=data.queue_code,
        node_ip=data.node_ip,
        node_hostname=data.node_hostname
    )
    return SuccessResponse(data=result, msg="注册成功")


