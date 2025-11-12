# -*- coding: utf-8 -*-
"""
服务模块路由
"""

from fastapi import APIRouter, Depends, Path, Body
from fastapi.responses import JSONResponse

from app.common.response import SuccessResponse
from app.core.router_class import OperationLogRoute
from app.core.dependencies import AuthPermission
from app.core.base_params import PaginationQueryParam
from app.core.logger import logger
from app.api.v1.module_system.auth.schema import AuthSchema

from .param import ServiceQueryParam
from .schema import ServiceCreateSchema, ServiceUpdateSchema
from .service import ServiceService

router = APIRouter(route_class=OperationLogRoute, prefix="/node/service", tags=["服务模块管理"])


@router.get("/tree", summary="查询服务模块树", description="查询服务模块树（包含节点）")
async def get_service_tree_controller(
    search: ServiceQueryParam = Depends(),
    auth: AuthSchema = Depends(AuthPermission(["operations:node:query"])),
) -> JSONResponse:
    order_by = [{"created_at": "desc"}]
    result = await ServiceService.get_service_tree_service(
        search=search.__dict__,
        order_by=order_by,
        auth=auth,
    )
    logger.info("查询服务模块树成功")
    return SuccessResponse(data=result, msg="查询服务模块树成功")


@router.get("/page", summary="分页查询服务模块", description="分页查询服务模块")
async def get_service_page_controller(
    page: PaginationQueryParam = Depends(),
    search: ServiceQueryParam = Depends(),
    auth: AuthSchema = Depends(AuthPermission(["operations:node:query"])),
) -> JSONResponse:
    result = await ServiceService.get_service_page_service(
        auth=auth,
        page_no=page.page_no or 1,
        page_size=page.page_size or 10,
        search=search,
        order_by=page.order_by,
    )
    logger.info("分页查询服务模块成功")
    return SuccessResponse(data=result, msg="查询服务模块成功")


@router.get("/detail/{id}", summary="查询服务模块详情", description="查询服务模块详情")
async def get_service_detail_controller(
    id: int = Path(..., description="服务模块ID"),
    auth: AuthSchema = Depends(AuthPermission(["operations:node:query"])),
) -> JSONResponse:
    result = await ServiceService.get_service_detail_service(id=id, auth=auth)
    logger.info(f"查询服务模块详情成功 {id}")
    return SuccessResponse(data=result, msg="查询服务模块详情成功")


@router.post("/create", summary="创建服务模块", description="创建服务模块")
async def create_service_controller(
    data: ServiceCreateSchema,
    auth: AuthSchema = Depends(AuthPermission(["operations:node:create"])),
) -> JSONResponse:
    result = await ServiceService.create_service_service(data=data, auth=auth)
    logger.info(f"创建服务模块成功: {result}")
    return SuccessResponse(data=result, msg="创建服务模块成功")


@router.put("/update/{id}", summary="修改服务模块", description="修改服务模块")
async def update_service_controller(
    data: ServiceUpdateSchema,
    id: int = Path(..., description="服务模块ID"),
    auth: AuthSchema = Depends(AuthPermission(["operations:node:update"])),
) -> JSONResponse:
    result = await ServiceService.update_service_service(auth=auth, id=id, data=data)
    logger.info(f"修改服务模块成功: {result}")
    return SuccessResponse(data=result, msg="修改服务模块成功")


@router.delete("/delete", summary="删除服务模块", description="删除服务模块")
async def delete_service_controller(
    ids: list[int] = Body(..., description="ID列表"),
    auth: AuthSchema = Depends(AuthPermission(["operations:node:delete"])),
) -> JSONResponse:
    await ServiceService.delete_service_service(ids=ids, auth=auth)
    logger.info(f"删除服务模块成功: {ids}")
    return SuccessResponse(msg="删除服务模块成功")

