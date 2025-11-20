# -*- coding: utf-8 -*-
"""
运维 Prometheus 配置接口
"""

from fastapi import APIRouter, Depends, Body, Path
from fastapi.responses import JSONResponse

from app.common.response import SuccessResponse
from app.core.router_class import OperationLogRoute
from app.core.dependencies import AuthPermission, get_current_user_by_query
from app.api.v1.module_system.auth.schema import AuthSchema

from .param import PrometheusJobQueryParam
from .schema import (
    PrometheusJobCreateSchema,
    PrometheusJobUpdateSchema,
    PrometheusConfigImportSchema,
)
from .service import PrometheusService


PrometheusRouter = APIRouter(route_class=OperationLogRoute, prefix="/prometheus", tags=["Prometheus配置"])


@PrometheusRouter.get(
    "/job/tree",
    summary="查询 Job 树形结构",
    description="按 Job 列出 Endpoint 树形结构",
    dependencies=[Depends(AuthPermission(["operations:prometheus:query"]))],
)
async def list_prometheus_job_tree_controller(
    search: PrometheusJobQueryParam = Depends(),
    auth: AuthSchema = Depends(AuthPermission(["operations:prometheus:query"])),
):
    result = await PrometheusService.list_job_tree_service(auth=auth, search=search)
    return SuccessResponse(data=result, msg="查询成功")


@PrometheusRouter.post(
    "/job",
    summary="新增 Job 配置",
    dependencies=[Depends(AuthPermission(["operations:prometheus:add"]))],
)
async def create_prometheus_job_controller(
    data: PrometheusJobCreateSchema,
    auth: AuthSchema = Depends(AuthPermission(["operations:prometheus:add"])),
):
    result = await PrometheusService.create_job_service(auth=auth, data=data)
    return SuccessResponse(data=result, msg="创建成功")


@PrometheusRouter.put(
    "/job/{job_id}",
    summary="修改 Job 配置",
    dependencies=[Depends(AuthPermission(["operations:prometheus:edit"]))],
)
async def update_prometheus_job_controller(
    job_id: int = Path(..., description="Job ID"),
    data: PrometheusJobUpdateSchema = Body(...),
    auth: AuthSchema = Depends(AuthPermission(["operations:prometheus:edit"])),
):
    result = await PrometheusService.update_job_service(auth=auth, job_id=job_id, data=data)
    return SuccessResponse(data=result, msg="更新成功")


@PrometheusRouter.get(
    "/job/{job_id}",
    summary="获取 Job 详情",
    dependencies=[Depends(AuthPermission(["operations:prometheus:query"]))],
)
async def get_prometheus_job_detail_controller(
    job_id: int = Path(..., description="Job ID"),
    auth: AuthSchema = Depends(AuthPermission(["operations:prometheus:query"])),
):
    result = await PrometheusService.get_job_detail_service(auth=auth, job_id=job_id)
    return SuccessResponse(data=result, msg="获取成功")


@PrometheusRouter.delete(
    "/job",
    summary="删除 Job",
    dependencies=[Depends(AuthPermission(["operations:prometheus:delete"]))],
)
async def delete_prometheus_job_controller(
    ids: list[int] = Body(..., embed=True, description="Job ID 列表"),
    auth: AuthSchema = Depends(AuthPermission(["operations:prometheus:delete"])),
):
    await PrometheusService.delete_job_service(auth=auth, ids=ids)
    return SuccessResponse(msg="删除成功")


@PrometheusRouter.get(
    "/job/export",
    summary="导出 Job 配置",
    dependencies=[Depends(AuthPermission(["operations:prometheus:export"]))],
)
async def export_prometheus_job_controller(
    auth: AuthSchema = Depends(AuthPermission(["operations:prometheus:export"])),
):
    result = await PrometheusService.export_job_config_service(auth=auth)
    return SuccessResponse(data=result, msg="导出成功")


@PrometheusRouter.post(
    "/job/import",
    summary="导入 Job 配置",
    dependencies=[Depends(AuthPermission(["operations:prometheus:import"]))],
)
async def import_prometheus_job_controller(
    data: PrometheusConfigImportSchema,
    auth: AuthSchema = Depends(AuthPermission(["operations:prometheus:import"])),
):
    result = await PrometheusService.import_job_config_service(auth=auth, data=data)
    return SuccessResponse(data=result, msg="导入成功")


@PrometheusRouter.get(
    "/http_sd",
    summary="Prometheus HTTP SD 接口",
    description="提供给 Prometheus 的 http_sd_configs 数据源，需要通过 token 访问",
)
async def prometheus_http_sd_controller(
    auth: AuthSchema = Depends(get_current_user_by_query),
):
    _ = auth  # 认证通过即可
    sd_items = await PrometheusService.http_sd_config_service()
    return JSONResponse(content=[item.model_dump() for item in sd_items])

