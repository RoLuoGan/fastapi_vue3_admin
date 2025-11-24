import uuid
import time
from datetime import datetime
from typing import Optional, Dict, Any
from fastapi import UploadFile
from redis.asyncio.client import Redis

from app.core.exceptions import CustomException
from app.core.logger import logger
from app.api.v1.module_system.auth.schema import AuthSchema
from app.api.v1.module_operations.models import ServicePackageModel
from app.api.v1.module_operations.service_package.crud import ServicePackageCRUD
from app.api.v1.module_operations.service_package.schema import ServicePackageCreateSchema, ServicePackageUpdateSchema, OneClickUploadSchema, ServicePackageOutSchema
from app.api.v1.module_operations.service_package.param import ServicePackageQueryParam
from app.api.v1.module_operations.service_module.crud import ServiceCRUD
from app.utils.oss_util import OSSUtil

class ServicePackageService:
    
    @classmethod
    async def create_package_service(cls, auth: AuthSchema, redis: Redis, data: ServicePackageCreateSchema, file: Optional[UploadFile] = None) -> Dict:
        service = await ServiceCRUD(auth).get_obj_by_id_crud(data.service_id)
        if not service:
            raise CustomException(msg="Service module not found")

        # Generate version if not provided
        if not data.version:
            data.version = datetime.now().strftime("%Y%m%d%H%M%S") + "00"

        # Handle File Upload
        if file:
            # Path format: /{system}/{date}/{module_name}_{timestamp}_{uuid}.tgz
            system_name = "paas" # Default
            date_str = datetime.now().strftime("%Y%m%d")
            timestamp_str = datetime.now().strftime("%Y%m%d%H%M%S")
            uuid_str = str(uuid.uuid4())[:8]
            ext = file.filename.split('.')[-1] if '.' in file.filename else 'tgz'
            
            target_path = f"{system_name}/{date_str}/{service.name}_{timestamp_str}_{uuid_str}.{ext}"
            
            content = await file.read()
            upload_result = await OSSUtil.upload_file(redis, target_path, content)
            
            data.package_path = target_path
            data.md5 = upload_result.get("etag")
            data.size = len(content) # Or use UploadFile size if reliable, but content len is safer
        
        elif not data.package_path:
            raise CustomException(msg="Package path is required if no file is uploaded")

        # 保存 is_latest 标志，因为模型中没有这个字段
        is_latest = data.is_latest
        
        # 创建数据字典，排除 is_latest 字段（模型中没有这个字段）
        create_data = data.model_dump(exclude={'is_latest'})
        
        # Create DB Record
        obj = await ServicePackageCRUD(auth).create_obj_crud(data=create_data)
        
        # Update Service Module if is_latest
        if is_latest:
            await ServiceCRUD(auth).update_obj_crud(service.id, {"current_package_version": data.version})
            
        return ServicePackageOutSchema.model_validate(obj).model_dump()

    @classmethod
    async def update_package_service(cls, auth: AuthSchema, id: int, data: ServicePackageUpdateSchema) -> Dict:
        obj = await ServicePackageCRUD(auth).get_obj_by_id_crud(id)
        if not obj:
            raise CustomException(msg="Package not found")
        
        # 保存 is_latest 标志，因为模型中没有这个字段
        is_latest = data.is_latest
        
        # 更新数据字典，排除 is_latest 字段
        update_data = data.model_dump(exclude={'is_latest'}, exclude_unset=True)
        updated_obj = await ServicePackageCRUD(auth).update_obj_crud(id, update_data)
        
        if is_latest:
            await ServiceCRUD(auth).update_obj_crud(updated_obj.service_id, {"current_package_version": updated_obj.version})
            
        return ServicePackageOutSchema.model_validate(updated_obj).model_dump()

    @classmethod
    async def delete_package_service(cls, auth: AuthSchema, ids: list[int]):
        # Check if any package is currently used by its service
        for id in ids:
            pkg = await ServicePackageCRUD(auth).get_obj_by_id_crud(id)
            if not pkg:
                continue
            service = await ServiceCRUD(auth).get_obj_by_id_crud(pkg.service_id)
            if service and service.current_package_version == pkg.version:
                raise CustomException(msg=f"Package {pkg.version} is currently in use by service {service.name} and cannot be deleted.")
                
            # Optional: Delete from OSS? Spec doesn't explicitly say, but usually good practice. 
            # But maybe we keep history? The spec says "Delete logic: Packages managed by service module cannot be deleted".
            # It implies if not managed (current), can be deleted.
            # I won't delete from OSS to be safe unless requested.
            
        await ServicePackageCRUD(auth).delete_obj_crud(ids)

    @classmethod
    async def one_click_upload_service(cls, auth: AuthSchema, redis: Redis, data: OneClickUploadSchema) -> Dict:
        service = await ServiceCRUD(auth).get_obj_by_id_crud(data.service_id)
        if not service:
            raise CustomException(msg="Service module not found")

        # Source Path Logic
        # Spec: /{date}/{module_name}/{module_name}.tgz
        # Date defaults to today MMDD or user provided
        now = datetime.now()
        if data.date_str:
            date_part = data.date_str
        else:
            date_part = now.strftime("%m%d") # e.g. 1123
            
        source_path = f"/{date_part}/{service.name}/{service.name}.tgz"
        # Remove leading slash if OSS SDK doesn't like it? OSS usually doesn't care or prefers no leading slash. 
        # But let's try with/without. Usually keys don't start with /.
        if source_path.startswith("/"):
            source_path = source_path[1:]

        # Target Path Logic
        # Spec: {system}/{date}/{module_name}_{timestamp}_{uuid}.tgz
        # System: paas
        # Date: YYYYMMDD (e.g. 20251113)
        system_name = "paas"
        target_date = now.strftime("%Y%m%d")
        timestamp_str = now.strftime("%Y%m%d%H%M%S")
        uuid_str = str(uuid.uuid4())[:8]
        target_path = f"{system_name}/{target_date}/{service.name}_{timestamp_str}_{uuid_str}.tgz"

        # Check Source & Copy
        try:
            meta = await OSSUtil.get_object_meta(redis, source_path)
        except Exception as e:
            logger.error(f"Failed to find source package at {source_path}: {e}")
            # Try with leading slash if failed? Or maybe date format is different?
            raise CustomException(msg=f"Source package not found at {source_path}. Please ensure file exists in OSS.")

        await OSSUtil.copy_file(redis, source_path, target_path)

        # Create Package Record
        # 注意：is_latest 不在模型中，需要单独处理
        pkg_data = ServicePackageCreateSchema(
            service_id=service.id,
            version=timestamp_str + "00", # Use timestamp as version? Spec: "Version (auto generated... 2025112214300100)"
            package_path=target_path,
            md5=meta.get("etag"),
            size=meta.get("size"),
            is_latest=True
        )
        
        # 创建数据字典，排除 is_latest 字段
        create_data = pkg_data.model_dump(exclude={'is_latest'})
        pkg = await ServicePackageCRUD(auth).create_obj_crud(data=create_data)
        
        # Update Service
        await ServiceCRUD(auth).update_obj_crud(service.id, {"current_package_version": pkg.version})
        
        return ServicePackageOutSchema.model_validate(pkg).model_dump()

    @classmethod
    async def get_package_list_service(cls, auth: AuthSchema, search: ServicePackageQueryParam) -> list[Dict]:
        # Basic list by service_id
        # If service_id not in search, return empty or all? Usually we filter by service.
        if not search.service_id:
            # Maybe return all?
            pass
        
        # Helper to get list. ServicePackageCRUD doesn't have generic get_list with search params unless I add it.
        # Or I can use CRUDBase methods if they support the search dict.
        # CRUDBase get_obj_list_crud uses search dict.
        
        crud = ServicePackageCRUD(auth)
        # Construct search dict
        search_dict = {}
        if search.service_id:
            search_dict["service_id"] = search.service_id
        if search.version:
            search_dict["version"] = search.version
            
        objs = await crud.get_obj_list_crud(search=search_dict, order_by=[{"created_at": "desc"}])
        return [ServicePackageOutSchema.model_validate(obj).model_dump() for obj in objs]

