from typing import Optional
from fastapi import Query
from pydantic import BaseModel

class ServicePackageQueryParam(BaseModel):
    service_id: Optional[int] = Query(None, description="服务模块ID")
    version: Optional[str] = Query(None, description="版本号")

