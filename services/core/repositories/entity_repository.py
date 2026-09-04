"""Entity Repository - Manages Entity domain objects."""
from typing import Optional, Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from services.core.models.models import Entity
from services.core.repositories.base import TenantAwareRepository


class EntityRepository(TenantAwareRepository[Entity]):
    """Repository for Entity domain operations."""

    def __init__(self, session: AsyncSession):
        super().__init__(session, model=Entity)

    async def get_by_id(
        self, entity_id: UUID, tenant_id: Optional[UUID] = None
    ) -> Optional[Entity]:
        """Get entity by ID with optional tenant filter."""
        stmt = select(Entity).where(Entity.id == entity_id)

        if tenant_id:
            stmt = stmt.where(Entity.tenant_id == tenant_id)

        # Exclude soft-deleted
        stmt = stmt.where(Entity.deleted_at.is_(None))

        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_type(
        self,
        entity_type: str,
        tenant_id: Optional[UUID] = None,
        limit: int = 20,
        offset: int = 0
    ) -> Sequence[Entity]:
        """List entities by type with pagination."""
        stmt = (
            select(Entity)
            .where(Entity.entity_type == entity_type)
            .where(Entity.deleted_at.is_(None))
            .offset(offset)
            .limit(limit)
        )

        if tenant_id:
            stmt = stmt.where(Entity.tenant_id == tenant_id)

        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def find_by_name(
        self,
        name: str,
        tenant_id: Optional[UUID] = None
    ) -> Optional[Entity]:
        """Find entity by exact name match."""
        stmt = (
            select(Entity)
            .where(Entity.name == name)
            .where(Entity.deleted_at.is_(None))
        )

        if tenant_id:
            stmt = stmt.where(Entity.tenant_id == tenant_id)

        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def search(
        self,
        query: str,
        tenant_id: Optional[UUID] = None,
        limit: int = 20,
        offset: int = 0
    ) -> Sequence[Entity]:
        """Search entities by name (case-insensitive partial match)."""
        stmt = (
            select(Entity)
            .where(Entity.name.ilike(f"%{query}%"))
            .where(Entity.deleted_at.is_(None))
            .offset(offset)
            .limit(limit)
        )

        if tenant_id:
            stmt = stmt.where(Entity.tenant_id == tenant_id)

        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def create(self, entity: Entity) -> Entity:
        """Create a new entity. Caller must commit transaction."""
        self.session.add(entity)
        await self.session.flush()
        await self.session.refresh(entity)
        return entity

    async def update(self, entity: Entity) -> Entity:
        """Update an existing entity. Caller must commit transaction."""
        await self.session.merge(entity)
        await self.session.flush()
        return entity

    async def soft_delete(self, entity_id: UUID, tenant_id: Optional[UUID] = None) -> bool:
        """Soft delete an entity."""
        entity = await self.get_by_id(entity_id, tenant_id)
        if entity is None:
            return False

        entity.soft_delete()
        await self.session.flush()
        return True

    # Backward compatibility aliases for service layer
    async def list_by_tenant(
        self,
        tenant_id: str,
        entity_type: Optional[str] = None,
        skip: int = 0,
        limit: int = 20
    ):
        """Alias for list with tenant filter (service layer compat)."""
        from uuid import UUID as _UUID
        tid = _UUID(tenant_id) if isinstance(tenant_id, str) else tenant_id
        return await self.list_by_type(entity_type or "", tid, limit, skip)

    async def update_entity(self, entity_id: str, tenant_id: str, **kwargs) -> Optional[Entity]:
        """Update entity by ID (service layer compat)."""
        from uuid import UUID as _UUID
        eid = _UUID(entity_id)
        tid = _UUID(tenant_id)
        entity = await self.get_by_id(eid, tid)
        if entity is None:
            return None
        for key, value in kwargs.items():
            if hasattr(entity, key):
                setattr(entity, key, value)
        await self.session.merge(entity)
        await self.session.flush()
        return entity

    async def delete_entity(self, entity_id: str, tenant_id: str) -> bool:
        """Alias for soft_delete (service layer compat)."""
        from uuid import UUID as _UUID
        return await self.soft_delete(_UUID(entity_id), _UUID(tenant_id))
