"""TwinRelationshipRepository — Data access for twin relationships."""
from typing import Optional, Sequence
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from services.core.repositories.base import TenantAwareRepository
from services.twin_graph.models import TwinRelationship


class TwinRelationshipRepository(TenantAwareRepository[TwinRelationship]):
    """Repository for twin relationship persistence."""

    def __init__(self, session: AsyncSession):
        super().__init__(session, model=TwinRelationship)

    async def get_by_ids(
        self, source_id: UUID, target_id: UUID, tenant_id: UUID
    ) -> Optional[TwinRelationship]:
        """Get a specific relationship between two entities within tenant."""
        stmt = select(TwinRelationship).where(
            TwinRelationship.source_twin_id == source_id,
            TwinRelationship.target_twin_id == target_id,
            TwinRelationship.tenant_id == tenant_id,
            TwinRelationship.deleted_at.is_(None),
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_source_relationships(
        self, source_id: UUID, tenant_id: UUID, limit: int = 100
    ) -> Sequence[TwinRelationship]:
        """List all outgoing relationships from a source entity."""
        stmt = select(TwinRelationship).where(
            TwinRelationship.source_twin_id == source_id,
            TwinRelationship.tenant_id == tenant_id,
            TwinRelationship.deleted_at.is_(None),
        ).limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def list_target_relationships(
        self, target_id: UUID, tenant_id: UUID, limit: int = 100
    ) -> Sequence[TwinRelationship]:
        """List all incoming relationships to a target entity."""
        stmt = select(TwinRelationship).where(
            TwinRelationship.target_twin_id == target_id,
            TwinRelationship.tenant_id == tenant_id,
            TwinRelationship.deleted_at.is_(None),
        ).limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def list_by_type(
        self, relationship_type: str, tenant_id: UUID, limit: int = 100
    ) -> Sequence[TwinRelationship]:
        """List all relationships of a given type within tenant."""
        stmt = select(TwinRelationship).where(
            TwinRelationship.relationship_type == relationship_type,
            TwinRelationship.tenant_id == tenant_id,
            TwinRelationship.deleted_at.is_(None),
        ).limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def count_by_type(self, relationship_type: str, tenant_id: UUID) -> int:
        """Count relationships of a given type within tenant."""
        stmt = select(func.count()).select_from(TwinRelationship).where(
            TwinRelationship.relationship_type == relationship_type,
            TwinRelationship.tenant_id == tenant_id,
            TwinRelationship.deleted_at.is_(None),
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()
