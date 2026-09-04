"""EntityRepository — Data access for PersistentTwinEntity."""
from typing import Optional, Sequence
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from services.core.repositories.base import TenantAwareRepository
from services.twin.models.entity import PersistentTwinEntity


class EntityRepository(TenantAwareRepository[PersistentTwinEntity]):
    """Repository for TwinEntity persistence operations."""

    def __init__(self, session: AsyncSession):
        super().__init__(session, model=PersistentTwinEntity)

    async def get_by_external_id(self, external_id: str, tenant_id: UUID) -> Optional[PersistentTwinEntity]:
        """Get entity by external ID within tenant scope."""
        stmt = select(PersistentTwinEntity).where(
            PersistentTwinEntity.external_id == external_id,
            PersistentTwinEntity.tenant_id == tenant_id,
            PersistentTwinEntity.deleted_at.is_(None)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_definition(
        self, definition_id: UUID, tenant_id: UUID, limit: int = 100, offset: int = 0
    ) -> Sequence[PersistentTwinEntity]:
        """List entities by definition type."""
        stmt = select(PersistentTwinEntity).where(
            PersistentTwinEntity.definition_id == definition_id,
            PersistentTwinEntity.tenant_id == tenant_id,
            PersistentTwinEntity.deleted_at.is_(None)
        ).offset(offset).limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def count_by_definition(self, definition_id: UUID, tenant_id: UUID) -> int:
        """Count entities by definition type."""
        stmt = select(func.count()).select_from(
            PersistentTwinEntity
        ).where(
            PersistentTwinEntity.definition_id == definition_id,
            PersistentTwinEntity.tenant_id == tenant_id,
            PersistentTwinEntity.deleted_at.is_(None)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()
