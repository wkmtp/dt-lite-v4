"""Property Repository - Manages PropertyDefinition and PropertyValue."""
from typing import Optional, Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from services.core.models.models import PropertyDefinition, PropertyValue
from services.core.repositories.base import TenantAwareRepository


class PropertyRepository(TenantAwareRepository[PropertyDefinition]):
    """Repository for Property domain operations."""

    def __init__(self, session: AsyncSession):
        super().__init__(session, model=PropertyDefinition)

    async def get_definition(
        self,
        definition_id: UUID,
        tenant_id: Optional[UUID] = None
    ) -> Optional[PropertyDefinition]:
        """Get property definition by ID."""
        stmt = select(PropertyDefinition).where(PropertyDefinition.id == definition_id)

        # System-level definitions have NULL tenant_id
        if tenant_id is not None:
            stmt = stmt.where(
                (PropertyDefinition.tenant_id == tenant_id) |
                (PropertyDefinition.tenant_id.is_(None))
            )

        stmt = stmt.where(PropertyDefinition.deleted_at.is_(None))

        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_definition_by_key(
        self,
        entity_type: str,
        key: str,
        tenant_id: Optional[UUID] = None
    ) -> Optional[PropertyDefinition]:
        """Get property definition by entity_type and key."""
        stmt = select(PropertyDefinition).where(
            PropertyDefinition.entity_type == entity_type,
            PropertyDefinition.key == key,
            PropertyDefinition.deleted_at.is_(None)
        )

        if tenant_id is not None:
            stmt = stmt.where(
                (PropertyDefinition.tenant_id == tenant_id) |
                (PropertyDefinition.tenant_id.is_(None))
            )

        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_definitions(
        self,
        entity_type: Optional[str] = None,
        tenant_id: Optional[UUID] = None,
        limit: int = 50,
        offset: int = 0
    ) -> Sequence[PropertyDefinition]:
        """List property definitions."""
        stmt = select(PropertyDefinition).where(PropertyDefinition.deleted_at.is_(None))

        if entity_type:
            stmt = stmt.where(PropertyDefinition.entity_type == entity_type)

        if tenant_id is not None:
            stmt = stmt.where(
                (PropertyDefinition.tenant_id == tenant_id) |
                (PropertyDefinition.tenant_id.is_(None))
            )

        stmt = stmt.offset(offset).limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def create_definition(self, definition: PropertyDefinition) -> PropertyDefinition:
        """Create a new property definition. Caller must commit."""
        self.session.add(definition)
        await self.session.flush()
        await self.session.refresh(definition)
        return definition

    async def update_definition(self, definition: PropertyDefinition) -> PropertyDefinition:
        """Update a property definition. Caller must commit."""
        await self.session.merge(definition)
        await self.session.flush()
        return definition

    async def soft_delete_definition(self, definition_id: UUID) -> bool:
        """Soft delete a property definition."""
        definition = await self.get_definition(definition_id)
        if definition is None:
            return False

        definition.soft_delete()
        await self.session.flush()
        return True

    # ---- PropertyValue operations ----

    async def set_property(
        self,
        entity_id: UUID,
        definition_id: UUID,
        value: dict
    ) -> PropertyValue:
        """Set or update a property value."""
        stmt = select(PropertyValue).where(
            PropertyValue.entity_id == entity_id,
            PropertyValue.property_definition_id == definition_id
        )
        result = await self.session.execute(stmt)
        prop_value = result.scalar_one_or_none()

        if prop_value:
            prop_value.value = value
            prop_value.updated_at = self._now()
        else:
            prop_value = PropertyValue(
                entity_id=entity_id,
                property_definition_id=definition_id,
                value=value
            )
            self.session.add(prop_value)

        await self.session.flush()
        return prop_value

    async def get_properties(
        self,
        entity_id: UUID
    ) -> Sequence[PropertyValue]:
        """Get all properties for an entity."""
        stmt = (
            select(PropertyValue)
            .where(PropertyValue.entity_id == entity_id)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_property(
        self,
        entity_id: UUID,
        definition_id: UUID
    ) -> Optional[PropertyValue]:
        """Get a single property value."""
        stmt = select(PropertyValue).where(
            PropertyValue.entity_id == entity_id,
            PropertyValue.property_definition_id == definition_id
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    # Alias methods for backward compatibility with service layer
    async def list_by_entity_type(
        self,
        entity_type: str,
        tenant_id: Optional[UUID] = None,
        limit: int = 50,
        offset: int = 0
    ) -> Sequence[PropertyDefinition]:
        """Alias for list_definitions by entity_type."""
        return await self.list_definitions(entity_type, tenant_id, limit, offset)

    async def set_value(self, entity_id: UUID, definition_id: UUID, value: dict) -> PropertyValue:
        """Alias for set_property."""
        return await self.set_property(entity_id, definition_id, value)

    async def get_value(self, entity_id: UUID, definition_id: UUID) -> Optional[dict]:
        """Get property value."""
        pv = await self.get_property(entity_id, definition_id)
        return pv.value if pv else None

    @staticmethod
    def _now():
        from datetime import datetime, timezone
        return datetime.now(timezone.utc)
