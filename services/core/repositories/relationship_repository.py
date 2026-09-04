"""Relationship Repository - Manages entity relationships."""
from typing import Optional, Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from services.core.models.models import Relationship
from services.core.repositories.base import TenantAwareRepository


class RelationshipRepository(TenantAwareRepository[Relationship]):
    """Repository for Relationship domain operations."""

    def __init__(self, session: AsyncSession):
        super().__init__(session, model=Relationship)

    async def create_relation(
        self,
        tenant_id: UUID,
        source_entity_id: UUID,
        target_entity_id: UUID,
        relation_type: str
    ) -> Relationship:
        """Create a new relationship. Caller must commit."""
        rel = Relationship(
            tenant_id=tenant_id,
            source_entity_id=source_entity_id,
            target_entity_id=target_entity_id,
            relation_type=relation_type
        )
        self.session.add(rel)
        await self.session.flush()
        await self.session.refresh(rel)
        return rel

    async def delete_relation(self, relation_id: UUID, tenant_id: UUID) -> bool:
        """Soft delete a relationship."""
        rel = await self.get_by_id(relation_id)
        if rel is None or rel.tenant_id != tenant_id:
            return False

        rel.soft_delete()
        await self.session.flush()
        return True

    async def list_source_relations(
        self,
        entity_id: UUID,
        tenant_id: Optional[UUID] = None
    ) -> Sequence[Relationship]:
        """List all relationships where entity is the source."""
        stmt = (
            select(Relationship)
            .where(Relationship.source_entity_id == entity_id)
            .where(Relationship.deleted_at.is_(None))
        )

        if tenant_id:
            stmt = stmt.where(Relationship.tenant_id == tenant_id)

        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def list_target_relations(
        self,
        entity_id: UUID,
        tenant_id: Optional[UUID] = None
    ) -> Sequence[Relationship]:
        """List all relationships where entity is the target."""
        stmt = (
            select(Relationship)
            .where(Relationship.target_entity_id == entity_id)
            .where(Relationship.deleted_at.is_(None))
        )

        if tenant_id:
            stmt = stmt.where(Relationship.tenant_id == tenant_id)

        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def list_by_type(
        self,
        relation_type: str,
        tenant_id: Optional[UUID] = None,
        limit: int = 50,
        offset: int = 0
    ) -> Sequence[Relationship]:
        """List relationships by type."""
        stmt = (
            select(Relationship)
            .where(Relationship.relation_type == relation_type)
            .where(Relationship.deleted_at.is_(None))
            .offset(offset)
            .limit(limit)
        )

        if tenant_id:
            stmt = stmt.where(Relationship.tenant_id == tenant_id)

        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_relationships_for_entity(
        self,
        entity_id: UUID,
        tenant_id: Optional[UUID] = None
    ) -> Sequence[Relationship]:
        """Get all relationships involving an entity (as source or target)."""
        stmt = (
            select(Relationship)
            .where(
                (Relationship.source_entity_id == entity_id) |
                (Relationship.target_entity_id == entity_id)
            )
            .where(Relationship.deleted_at.is_(None))
        )

        if tenant_id:
            stmt = stmt.where(Relationship.tenant_id == tenant_id)

        result = await self.session.execute(stmt)
        return result.scalars().all()

    # Backward compatibility aliases for service layer
    async def list_by_entity(self, entity_id: UUID) -> Sequence[Relationship]:
        """Alias for get_relationships_for_entity (service layer compat)."""
        return await self.get_relationships_for_entity(entity_id)

    async def list_by_tenant(self, tenant_id: UUID) -> Sequence[Relationship]:
        """List all relationships for a tenant."""
        stmt = (
            select(Relationship)
            .where(Relationship.tenant_id == tenant_id)
            .where(Relationship.deleted_at.is_(None))
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def delete(self, rel_id: UUID) -> bool:
        """Alias for delete_relation (service layer compat)."""
        stmt = select(Relationship).where(Relationship.id == rel_id)
        result = await self.session.execute(stmt)
        rel = result.scalar_one_or_none()
        if rel is None:
            return False
        rel.soft_delete()
        await self.session.flush()
        return True
