"""DeviceEntityBinding Repository - Manages Device-Twin Binding domain objects."""
from typing import Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from services.core.repositories.base import TenantAwareRepository
from services.iota.models.models import DeviceEntityBinding


class DeviceEntityBindingRepository(TenantAwareRepository[DeviceEntityBinding]):
    """Repository for DeviceEntityBinding domain operations."""

    def __init__(self, session: AsyncSession):
        super().__init__(session, model=DeviceEntityBinding)

    async def get_by_device(self, device_id: UUID, tenant_id: UUID) -> Sequence[DeviceEntityBinding]:
        """Get all bindings for a device within tenant."""
        stmt = select(DeviceEntityBinding).where(
            DeviceEntityBinding.device_id == device_id,
            DeviceEntityBinding.tenant_id == tenant_id,
            DeviceEntityBinding.deleted_at.is_(None)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_by_entity(self, entity_id: UUID, tenant_id: UUID) -> Sequence[DeviceEntityBinding]:
        """Get all bindings for an entity within tenant."""
        stmt = select(DeviceEntityBinding).where(
            DeviceEntityBinding.entity_id == entity_id,
            DeviceEntityBinding.tenant_id == tenant_id,
            DeviceEntityBinding.deleted_at.is_(None)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def exists(self, device_id: UUID, entity_id: UUID, tenant_id: UUID) -> bool:
        """Check if binding exists between device and entity."""
        stmt = select(DeviceEntityBinding).where(
            DeviceEntityBinding.device_id == device_id,
            DeviceEntityBinding.entity_id == entity_id,
            DeviceEntityBinding.tenant_id == tenant_id,
            DeviceEntityBinding.deleted_at.is_(None)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none() is not None
