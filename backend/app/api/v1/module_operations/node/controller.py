# -*- coding: utf-8 -*-

from fastapi import APIRouter, Body, Depends, Path
from fastapi.responses import JSONResponse

from app.common.response import SuccessResponse
from app.core.router_class import OperationLogRoute
from app.core.dependencies import AuthPermission
from app.core.base_schema import BatchSetAvailable
from app.core.logger import logger
from ...module_system.auth.schema import AuthSchema
from .param import ServiceQueryParam, NodeQueryParam
from .service import ServiceService, NodeService, TaskService
from .schema import (
    ServiceCreateSchema,
    ServiceUpdateSchema,
    NodeCreateSchema,
    NodeUpdateSchema,
    NodeIdsSchema
)


NodeRouter = APIRouter(route_class=OperationLogRoute, prefix="/node", tags=["服务节点管理"])


@NodeRouter.get("/service/tree", summary="查询服务模块树", description="查询服务模块树（包含节点）")
async def get_service_tree_controller(
    search: ServiceQueryParam = Depends(),
    auth: AuthSchema = Depends(AuthPermission(["operations:node:query"]))
) -> JSONResponse:
    """查询服务模块树"""
    order_by = [{"created_at": "desc"}]
    result_dict_list = await ServiceService.get_service_tree_service(search=search, auth=auth, order_by=order_by)
    logger.info(f"查询服务模块树成功")
    return SuccessResponse(data=result_dict_list, msg="查询服务模块树成功")


@NodeRouter.get("/service/detail/{id}", summary="查询服务模块详情", description="查询服务模块详情")
async def get_service_detail_controller(
    id: int = Path(..., description="服务模块ID"),
    auth: AuthSchema = Depends(AuthPermission(["operations:node:query"]))
) -> JSONResponse:
    """查询服务模块详情"""
    result_dict = await ServiceService.get_service_detail_service(id=id, auth=auth)
    logger.info(f"查询服务模块详情成功 {id}")
    return SuccessResponse(data=result_dict, msg="查询服务模块详情成功")


@NodeRouter.post("/service/create", summary="创建服务模块", description="创建服务模块")
async def create_service_controller(
    data: ServiceCreateSchema,
    auth: AuthSchema = Depends(AuthPermission(["operations:node:create"]))
) -> JSONResponse:
    """创建服务模块"""
    result_dict = await ServiceService.create_service_service(data=data, auth=auth)
    logger.info(f"创建服务模块成功: {result_dict}")
    return SuccessResponse(data=result_dict, msg="创建服务模块成功")


@NodeRouter.put("/service/update/{id}", summary="修改服务模块", description="修改服务模块")
async def update_service_controller(
    data: ServiceUpdateSchema,
    id: int = Path(..., description="服务模块ID"),
    auth: AuthSchema = Depends(AuthPermission(["operations:node:update"]))
) -> JSONResponse:
    """修改服务模块"""
    result_dict = await ServiceService.update_service_service(auth=auth, id=id, data=data)
    logger.info(f"修改服务模块成功: {result_dict}")
    return SuccessResponse(data=result_dict, msg="修改服务模块成功")


@NodeRouter.delete("/service/delete", summary="删除服务模块", description="删除服务模块")
async def delete_service_controller(
    ids: list[int] = Body(..., description="ID列表"),
    auth: AuthSchema = Depends(AuthPermission(["operations:node:delete"]))
) -> JSONResponse:
    """删除服务模块"""
    await ServiceService.delete_service_service(ids=ids, auth=auth)
    logger.info(f"删除服务模块成功: {ids}")
    return SuccessResponse(msg="删除服务模块成功")


@NodeRouter.get("/node/detail/{id}", summary="查询节点详情", description="查询节点详情")
async def get_node_detail_controller(
    id: int = Path(..., description="节点ID"),
    auth: AuthSchema = Depends(AuthPermission(["operations:node:query"]))
) -> JSONResponse:
    """查询节点详情"""
    result_dict = await NodeService.get_node_detail_service(id=id, auth=auth)
    logger.info(f"查询节点详情成功 {id}")
    return SuccessResponse(data=result_dict, msg="查询节点详情成功")


@NodeRouter.post("/node/create", summary="创建节点", description="创建节点")
async def create_node_controller(
    data: NodeCreateSchema,
    auth: AuthSchema = Depends(AuthPermission(["operations:node:create"]))
) -> JSONResponse:
    """创建节点"""
    result_dict = await NodeService.create_node_service(data=data, auth=auth)
    logger.info(f"创建节点成功: {result_dict}")
    return SuccessResponse(data=result_dict, msg="创建节点成功")


@NodeRouter.put("/node/update/{id}", summary="修改节点", description="修改节点")
async def update_node_controller(
    data: NodeUpdateSchema,
    id: int = Path(..., description="节点ID"),
    auth: AuthSchema = Depends(AuthPermission(["operations:node:update"]))
) -> JSONResponse:
    """修改节点"""
    result_dict = await NodeService.update_node_service(auth=auth, id=id, data=data)
    logger.info(f"修改节点成功: {result_dict}")
    return SuccessResponse(data=result_dict, msg="修改节点成功")


@NodeRouter.delete("/node/delete", summary="删除节点", description="删除节点")
async def delete_node_controller(
    ids: list[int] = Body(..., description="ID列表"),
    auth: AuthSchema = Depends(AuthPermission(["operations:node:delete"]))
) -> JSONResponse:
    """删除节点"""
    await NodeService.delete_node_service(ids=ids, auth=auth)
    logger.info(f"删除节点成功: {ids}")
    return SuccessResponse(msg="删除节点成功")


@NodeRouter.post("/deploy", summary="部署服务", description="多样化服务部署（模拟）")
async def deploy_controller(
    data: NodeIdsSchema,
    auth: AuthSchema = Depends(AuthPermission(["operations:node:deploy"]))
) -> JSONResponse:
    """部署服务"""
    result_dict = await TaskService.deploy_service(node_ids=data.node_ids, auth=auth)
    logger.info(f"部署服务成功: {result_dict}")
    return SuccessResponse(data=result_dict, msg="部署任务已启动")


@NodeRouter.post("/restart", summary="重启服务", description="重启服务（模拟）")
async def restart_controller(
    data: NodeIdsSchema,
    auth: AuthSchema = Depends(AuthPermission(["operations:node:restart"]))
) -> JSONResponse:
    """重启服务"""
    result_dict = await TaskService.restart_service(node_ids=data.node_ids, auth=auth)
    logger.info(f"重启服务成功: {result_dict}")
    return SuccessResponse(data=result_dict, msg="重启任务已启动")


@NodeRouter.get("/task/recent", summary="查询最近任务", description="查询最近20个任务")
async def get_recent_tasks_controller(
    limit: int = 20,
    auth: AuthSchema = Depends(AuthPermission(["operations:node:query"]))
) -> JSONResponse:
    """查询最近任务"""
    result_dict_list = await TaskService.get_recent_tasks_service(limit=limit, auth=auth)
    logger.info(f"查询最近任务成功")
    return SuccessResponse(data=result_dict_list, msg="查询最近任务成功")

