from typing import Optional
from pydantic import BaseModel, Field

class ServicePackageQueryParam(BaseModel):
    service_id: Optional[int] = Field(None, description="服务模块ID")
    version: Optional[str] = Field(None, description="版本号")

