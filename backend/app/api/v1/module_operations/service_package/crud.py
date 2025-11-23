from typing import List, Optional
from sqlalchemy import select, desc
from app.core.base_crud import CRUDBase
from app.api.v1.module_operations.models import ServicePackageModel

class ServicePackageCRUD(CRUDBase[ServicePackageModel]):
    async def get_packages_by_service(self, service_id: int) -> List[ServicePackageModel]:
        stmt = select(self.model).where(self.model.service_id == service_id).order_by(desc(self.model.created_at))
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_by_service_and_version(self, service_id: int, version: str) -> Optional[ServicePackageModel]:
        stmt = select(self.model).where(self.model.service_id == service_id, self.model.version == version)
        result = await self.db.execute(stmt)
        return result.scalars().first()
