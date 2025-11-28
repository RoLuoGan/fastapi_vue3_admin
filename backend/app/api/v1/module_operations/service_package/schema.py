from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict

from app.core.validator import DateTimeStr

class ServicePackageBase(BaseModel):
    service_id: int
    version: Optional[str] = None
    package_path: Optional[str] = None
    md5: Optional[str] = None
    size: Optional[int] = None

class ServicePackageCreateSchema(ServicePackageBase):
    service_id: int
    is_latest: bool = True 
    # version is optional, if not provided, generate one
    pass

class ServicePackageUpdateSchema(BaseModel):
    version: Optional[str] = None
    package_path: Optional[str] = None
    md5: Optional[str] = None
    size: Optional[int] = None
    is_latest: bool = False

class ServicePackageOutSchema(ServicePackageBase):
    id: int
    version: str
    package_path: str
    created_at: Optional[DateTimeStr] = None
    updated_at: Optional[DateTimeStr] = None
    model_config = ConfigDict(from_attributes=True)

class OneClickUploadSchema(BaseModel):
    service_ids: list[int]
    date_str: Optional[str] = None # e.g. "1123" or "20251123"

