"""Device Repository - Manages Device domain objects."""
from typing import Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from services.core.repositories.base import TenantAwareRepository
from services.iota.models.models import Device


class DeviceRepository(TenantAwareRepository[Device]):
    """Repository for Device domain operations."""

    def __init__(self, session: AsyncSession):
        super().__init__(session, model=Device)

    async def get_by_external_id(
        self, external_id: str, tenant_id: UUID
    ) -> Device | None:
        """Get device by external ID within tenant."""
        stmt = select(Device).where(
            Device.external_id == external_id,
            Device.tenant_id == tenant_id,
            Device.deleted_at.is_(None)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_datasource(
        self, data_source_id: UUID, tenant_id: UUID,
        limit: int = 20, offset: int = 0
    ) -> Sequence[Device]:
        """List devices for a data source within tenant."""
        stmt = select(Device).where(
            Device.data_source_id == data_source_id,
            Device.tenant_id == tenant_id,
            Device.deleted_at.is_(None)
        ).offset(offset).limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def list_by_connection(
        self, connection_id: UUID, tenant_id: UUID,
        limit: int = 20, offset: int = 0
    ) -> Sequence[Device]:
        """List devices for a connection within tenant."""
        stmt = select(Device).where(
            Device.connection_id == connection_id,
            Device.tenant_id == tenant_id,
            Device.deleted_at.is_(None)
        ).offset(offset).limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()
