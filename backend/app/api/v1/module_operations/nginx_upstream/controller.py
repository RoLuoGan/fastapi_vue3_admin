# -*- coding: utf-8 -*-
"""
Nginx Upstream路由
"""

from fastapi import APIRouter, Depends, Path, Body
from fastapi.responses import JSONResponse

from app.common.response import SuccessResponse
from app.core.router_class import OperationLogRoute
from app.core.dependencies import AuthPermission
from app.core.base_params import PaginationQueryParam
from app.core.logger import logger
from app.api.v1.module_system.auth.schema import AuthSchema

from .param import NginxUpstreamQueryParam
from .schema import NginxUpstreamCreateSchema, NginxUpstreamUpdateSchema, SyncUpstreamSchema, PreviewTemplateSchema
from .service import NginxUpstreamService

router = APIRouter(route_class=OperationLogRoute, prefix="/nginx-upstream", tags=["Nginx Upstream管理"])


@router.get("/page", summary="分页查询Nginx Upstream", description="分页查询Nginx Upstream")
async def get_nginx_upstream_page_controller(
    page: PaginationQueryParam = Depends(),
    search: NginxUpstreamQueryParam = Depends(),
    auth: AuthSchema = Depends(AuthPermission(["operations:nginx_upstream:query"], check_data_scope=False)),
) -> JSONResponse:
    result = await NginxUpstreamService.get_upstream_page_service(
        auth=auth,
        page_no=page.page_no or 1,
        page_size=page.page_size or 10,
        search=search,
        order_by=page.order_by,
    )
    logger.info("分页查询Nginx Upstream成功")
    return SuccessResponse(data=result, msg="查询Nginx Upstream列表成功")


@router.get("/detail/{id}", summary="查询Nginx Upstream详情", description="查询Nginx Upstream详情")
async def get_nginx_upstream_detail_controller(
    id: int = Path(..., description="Nginx Upstream ID"),
    auth: AuthSchema = Depends(AuthPermission(["operations:nginx_upstream:query"], check_data_scope=False)),
) -> JSONResponse:
    result = await NginxUpstreamService.get_upstream_detail_service(id=id, auth=auth)
    logger.info(f"查询Nginx Upstream详情成功 {id}")
    return SuccessResponse(data=result, msg="查询Nginx Upstream详情成功")


@router.post("/create", summary="创建Nginx Upstream", description="创建Nginx Upstream")
async def create_nginx_upstream_controller(
    data: NginxUpstreamCreateSchema,
    auth: AuthSchema = Depends(AuthPermission(["operations:nginx_upstream:create"])),
) -> JSONResponse:
    result = await NginxUpstreamService.create_upstream_service(data=data, auth=auth)
    logger.info(f"创建Nginx Upstream成功: {result}")
    return SuccessResponse(data=result, msg="创建Nginx Upstream成功")


@router.put("/update/{id}", summary="修改Nginx Upstream", description="修改Nginx Upstream")
async def update_nginx_upstream_controller(
    data: NginxUpstreamUpdateSchema,
    id: int = Path(..., description="Nginx Upstream ID"),
    auth: AuthSchema = Depends(AuthPermission(["operations:nginx_upstream:update"])),
) -> JSONResponse:
    result = await NginxUpstreamService.update_upstream_service(auth=auth, id=id, data=data)
    logger.info(f"修改Nginx Upstream成功: {result}")
    return SuccessResponse(data=result, msg="修改Nginx Upstream成功")


@router.delete("/delete", summary="删除Nginx Upstream", description="删除Nginx Upstream")
async def delete_nginx_upstream_controller(
    ids: list[int] = Body(..., description="ID列表"),
    auth: AuthSchema = Depends(AuthPermission(["operations:nginx_upstream:delete"])),
) -> JSONResponse:
    await NginxUpstreamService.delete_upstream_service(ids=ids, auth=auth)
    logger.info(f"删除Nginx Upstream成功: {ids}")
    return SuccessResponse(msg="删除Nginx Upstream成功")


@router.post("/sync", summary="同步Nginx Upstream配置", description="同步Nginx Upstream配置到Nginx节点")
async def sync_nginx_upstream_controller(
    data: SyncUpstreamSchema,
    auth: AuthSchema = Depends(AuthPermission(["operations:nginx_upstream:sync"])),
) -> JSONResponse:
    result = await NginxUpstreamService.sync_upstream_service(auth=auth, upstream_ids=data.upstream_ids)
    logger.info(f"同步Nginx Upstream配置成功: {data.upstream_ids}")
    return SuccessResponse(data=result, msg="同步任务已创建")


@router.post("/preview-template", summary="预览Upstream模板", description="预览Upstream模板渲染结果")
async def preview_template_controller(
    data: PreviewTemplateSchema,
    auth: AuthSchema = Depends(AuthPermission(["operations:nginx_upstream:query"], check_data_scope=False)),
) -> JSONResponse:
    result = await NginxUpstreamService.preview_template_service(data=data)
    return SuccessResponse(data=result, msg="预览模板成功")
