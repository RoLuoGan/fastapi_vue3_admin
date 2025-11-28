from fastapi import APIRouter, Depends, UploadFile, File, Form, Body, Path
from fastapi.responses import JSONResponse
from redis.asyncio.client import Redis

from app.core.dependencies import AuthPermission, redis_getter
from app.common.response import SuccessResponse
from app.api.v1.module_system.auth.schema import AuthSchema
from app.core.router_class import OperationLogRoute

from .schema import ServicePackageCreateSchema, ServicePackageUpdateSchema, OneClickUploadSchema
from .param import ServicePackageQueryParam
from .service import ServicePackageService

router = APIRouter(route_class=OperationLogRoute, prefix="/service-package", tags=["服务软件包管理"])

@router.get("/list", summary="查询服务软件包列表")
async def get_list(
    search: ServicePackageQueryParam = Depends(),
    auth: AuthSchema = Depends(AuthPermission(["operations:package:query"])),
) -> JSONResponse:
    data = await ServicePackageService.get_package_list_service(auth, search)
    return SuccessResponse(data=data)

@router.post("/create", summary="创建服务软件包")
async def create(
    service_id: int = Form(...),
    version: str = Form(None),
    package_path: str = Form(None),
    md5: str = Form(None),
    is_latest: bool = Form(True),
    file: UploadFile = File(None),
    auth: AuthSchema = Depends(AuthPermission(["operations:package:create"])),
    redis: Redis = Depends(redis_getter)
) -> JSONResponse:
    data = ServicePackageCreateSchema(
        service_id=service_id,
        version=version,
        package_path=package_path,
        md5=md5,
        is_latest=is_latest
    )
    result = await ServicePackageService.create_package_service(auth, redis, data, file)
    return SuccessResponse(data=result)

@router.put("/update/{id}", summary="更新服务软件包")
async def update(
    id: int = Path(...),
    data: ServicePackageUpdateSchema = Body(...),
    auth: AuthSchema = Depends(AuthPermission(["operations:package:update"])),
) -> JSONResponse:
    result = await ServicePackageService.update_package_service(auth, id, data)
    return SuccessResponse(data=result)

@router.delete("/delete", summary="删除服务软件包")
async def delete(
    ids: list[int] = Body(..., embed=True),
    auth: AuthSchema = Depends(AuthPermission(["operations:package:delete"])),
) -> JSONResponse:
    await ServicePackageService.delete_package_service(auth, ids)
    return SuccessResponse(msg="Deleted successfully")

@router.post("/one-click-upload", summary="一键上传（支持批量）")
async def one_click_upload(
    data: OneClickUploadSchema,
    auth: AuthSchema = Depends(AuthPermission(["operations:package:create"])),
    redis: Redis = Depends(redis_getter)
) -> JSONResponse:
    result = await ServicePackageService.one_click_upload_service(auth, redis, data)
    return SuccessResponse(data=result, msg=f"成功上传 {len(result)} 个服务模块的版本包")

