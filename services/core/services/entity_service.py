"""Entity Service - Domain application service for Entity lifecycle."""
from typing import Optional
from uuid import UUID

from services.core.models.models import Entity
from services.core.schemas.entity import EntityCreate, EntityListResponse, EntityResponse
from services.core.unit_of_work import UnitOfWork
from services.events.domain_events import EntityCreated, EntityDeleted, EntityUpdated
from services.exceptions.base import EntityNotFound
from services.exceptions.entity import EntityDuplicateName, EntityNameRequired, EntityTypeRequired


def _to_response(entity: Entity) -> EntityResponse:
    """Convert Entity model to response DTO."""
    return EntityResponse(
        id=entity.id,
        tenant_id=entity.tenant_id,
        entity_type=entity.entity_type,
        name=entity.name,
        description=entity.description,
        status=entity.status,
        extra_data=entity.extra_data,
        created_at=entity.created_at,
        updated_at=entity.updated_at,
        deleted_at=entity.deleted_at,
    )


class EntityService:
    """Domain service for Entity operations."""

    def __init__(self, uow: UnitOfWork):
        self._uow = uow

    async def create_entity(
        self, data: EntityCreate, tenant_id: UUID
    ) -> tuple[EntityResponse, EntityCreated]:
        """Create a new entity with business rule validation."""
        if not data.name or not data.name.strip():
            raise EntityNameRequired()

        if not data.entity_type or not data.entity_type.strip():
            raise EntityTypeRequired()

        # Check duplicate name
        existing = await self._uow.entities.find_by_name(data.name.strip(), tenant_id)
        if existing is not None:
            raise EntityDuplicateName(data.name.strip(), str(tenant_id))

        entity = Entity(
            tenant_id=tenant_id,
            entity_type=data.entity_type.strip(),
            name=data.name.strip(),
            description=data.description,
            extra_data=data.extra_data,
        )

        entity = await self._uow.entities.create(entity)
        await self._uow.commit()

        event = EntityCreated(
            entity_id=entity.id,
            entity_type=entity.entity_type,
            name=entity.name,
            tenant_id=entity.tenant_id,
        )

        return _to_response(entity), event

    async def get_entity(
        self, entity_id: UUID, tenant_id: Optional[UUID] = None
    ) -> Optional[EntityResponse]:
        """Get entity by ID with optional tenant filter."""
        entity = await self._uow.entities.get_by_id(entity_id, tenant_id)
        if entity is None:
            return None
        return _to_response(entity)

    async def list_entities(
        self,
        entity_type: Optional[str] = None,
        tenant_id: Optional[UUID] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> EntityListResponse:
        """List entities with optional type filter and tenant isolation."""
        if entity_type:
            items = await self._uow.entities.list_by_type(entity_type, tenant_id, limit, offset)
        else:
            items = await self._uow.entities.list(tenant_id=tenant_id, limit=limit, offset=offset)

        return EntityListResponse(
            items=[_to_response(e) for e in items],
            total=len(items),
            limit=limit,
            offset=offset,
        )

    async def update_entity(
        self,
        entity_id: UUID,
        data: dict,
        tenant_id: Optional[UUID] = None,
    ) -> tuple[EntityResponse, EntityUpdated]:
        """Update an entity with validation."""
        entity = await self._uow.entities.get_by_id(entity_id, tenant_id)
        if entity is None:
            raise EntityNotFound(entity_id, "Entity")

        changes: dict = {}
        for field_name, value in data.items():
            if value is not None and hasattr(entity, field_name):
                old_value = getattr(entity, field_name)
                if old_value != value:
                    setattr(entity, field_name, value)
                    changes[field_name] = {"old": str(old_value), "new": str(value)}

        entity = await self._uow.entities.update(entity)
        await self._uow.commit()

        event = EntityUpdated(
            entity_id=entity.id,
            changes=changes,
            tenant_id=entity.tenant_id,
        )

        return _to_response(entity), event

    async def delete_entity(
        self, entity_id: UUID, tenant_id: Optional[UUID] = None
    ) -> tuple[bool, EntityDeleted]:
        """Soft delete an entity."""
        deleted = await self._uow.entities.soft_delete(entity_id, tenant_id)
        if deleted:
            await self._uow.commit()

        event = EntityDeleted(
            entity_id=entity_id,
            tenant_id=tenant_id or UUID(int=0),
        )

        return deleted, event

    @property
    def events(self):
        return {
            "entity_created": EntityCreated,
            "entity_updated": EntityUpdated,
            "entity_deleted": EntityDeleted,
        }
