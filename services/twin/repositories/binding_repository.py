"""BindingRepository — Data access for TwinBinding."""
from typing import Optional, Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from services.core.repositories.base import TenantAwareRepository
from services.twin.models.binding import TwinBinding


class BindingRepository(TenantAwareRepository[TwinBinding]):
    """Repository for TwinBinding persistence operations."""

    def __init__(self, session: AsyncSession):
        super().__init__(session, model=TwinBinding)

    async def get_by_device(self, device_id: UUID, tenant_id: UUID) -> Optional[TwinBinding]:
        """Get binding by device ID within tenant scope."""
        stmt = select(TwinBinding).where(
            TwinBinding.device_id == device_id,
            TwinBinding.tenant_id == tenant_id,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_entity(self, entity_id: UUID, tenant_id: UUID) -> Sequence[TwinBinding]:
        """List all bindings for a twin entity within tenant scope."""
        stmt = select(TwinBinding).where(
            TwinBinding.twin_entity_id == entity_id,
            TwinBinding.tenant_id == tenant_id,
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def exists(self, device_id: UUID, entity_id: UUID, tenant_id: UUID) -> bool:
        """Check if binding exists between device and entity."""
        stmt = select(TwinBinding).where(
            TwinBinding.device_id == device_id,
            TwinBinding.twin_entity_id == entity_id,
            TwinBinding.tenant_id == tenant_id,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none() is not None
