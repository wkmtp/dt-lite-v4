"""DataPoint Repository - Manages DataPoint domain objects."""
from typing import Optional, Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from services.core.repositories.base import TenantAwareRepository
from services.iota.models.models import DataPoint


class DataPointRepository(TenantAwareRepository[DataPoint]):
    """Repository for DataPoint domain operations."""

    def __init__(self, session: AsyncSession):
        super().__init__(session, model=DataPoint)

    async def get_by_device(self, device_id: UUID, tenant_id: UUID) -> Sequence[DataPoint]:
        """Get all data points for a device within tenant."""
        stmt = select(DataPoint).where(
            DataPoint.device_id == device_id,
            DataPoint.tenant_id == tenant_id,
            DataPoint.deleted_at.is_(None)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_by_key(self, key: str, device_id: UUID, tenant_id: UUID) -> Optional[DataPoint]:
        """Get data point by key within device and tenant."""
        stmt = select(DataPoint).where(
            DataPoint.key == key,
            DataPoint.device_id == device_id,
            DataPoint.tenant_id == tenant_id,
            DataPoint.deleted_at.is_(None)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_external_id(self, external_id: str, tenant_id: UUID) -> Optional[DataPoint]:
        """Get data point by external ID within tenant."""
        stmt = select(DataPoint).where(
            DataPoint.external_id == external_id,
            DataPoint.tenant_id == tenant_id,
            DataPoint.deleted_at.is_(None)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
