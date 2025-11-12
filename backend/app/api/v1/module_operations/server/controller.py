# -*- coding: utf-8 -*-
"""
服务器（节点）路由
"""

from fastapi import APIRouter, Depends, Path, Body
from fastapi.responses import JSONResponse

from app.common.response import SuccessResponse
from app.core.router_class import OperationLogRoute
from app.core.dependencies import AuthPermission
from app.core.base_params import PaginationQueryParam
from app.core.logger import logger
from app.api.v1.module_system.auth.schema import AuthSchema

from .param import ServerQueryParam
from .schema import ServerCreateSchema, ServerUpdateSchema
from .service import ServerService

router = APIRouter(route_class=OperationLogRoute, prefix="/node", tags=["服务器管理"])


@router.get("/node/page", summary="分页查询节点", description="分页查询节点")
async def get_server_page_controller(
    page: PaginationQueryParam = Depends(),
    search: ServerQueryParam = Depends(),
    auth: AuthSchema = Depends(AuthPermission(["operations:node:query"])),
) -> JSONResponse:
    result = await ServerService.get_server_page_service(
        auth=auth,
        page_no=page.page_no or 1,
        page_size=page.page_size or 10,
        search=search,
        order_by=page.order_by,
    )
    logger.info("分页查询节点成功")
    return SuccessResponse(data=result, msg="查询节点列表成功")


@router.get("/node/detail/{id}", summary="查询节点详情", description="查询节点详情")
async def get_server_detail_controller(
    id: int = Path(..., description="节点ID"),
    auth: AuthSchema = Depends(AuthPermission(["operations:node:query"])),
) -> JSONResponse:
    result = await ServerService.get_server_detail_service(id=id, auth=auth)
    logger.info(f"查询节点详情成功 {id}")
    return SuccessResponse(data=result, msg="查询节点详情成功")


@router.post("/node/create", summary="创建节点", description="创建节点")
async def create_server_controller(
    data: ServerCreateSchema,
    auth: AuthSchema = Depends(AuthPermission(["operations:node:create"])),
) -> JSONResponse:
    result = await ServerService.create_server_service(data=data, auth=auth)
    logger.info(f"创建节点成功: {result}")
    return SuccessResponse(data=result, msg="创建节点成功")


@router.put("/node/update/{id}", summary="修改节点", description="修改节点")
async def update_server_controller(
    data: ServerUpdateSchema,
    id: int = Path(..., description="节点ID"),
    auth: AuthSchema = Depends(AuthPermission(["operations:node:update"])),
) -> JSONResponse:
    result = await ServerService.update_server_service(auth=auth, id=id, data=data)
    logger.info(f"修改节点成功: {result}")
    return SuccessResponse(data=result, msg="修改节点成功")


@router.delete("/node/delete", summary="删除节点", description="删除节点")
async def delete_server_controller(
    ids: list[int] = Body(..., description="ID列表"),
    auth: AuthSchema = Depends(AuthPermission(["operations:node:delete"])),
) -> JSONResponse:
    await ServerService.delete_server_service(ids=ids, auth=auth)
    logger.info(f"删除节点成功: {ids}")
    return SuccessResponse(msg="删除节点成功")

