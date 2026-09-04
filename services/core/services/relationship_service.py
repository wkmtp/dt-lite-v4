"""Relationship Service - Domain application service for Entity relationship management.

Responsible for:
- Creating and deleting relationships between entities
- Querying graph edges (children/parents)
- Preventing self-loops
- Enforcing tenant isolation
"""
from uuid import UUID

from services.core.schemas.relationship import (
    RelationshipCreate,
    RelationshipResponse,
)
from services.core.unit_of_work import UnitOfWork
from services.events.domain_events import RelationshipCreated, RelationshipDeleted
from services.exceptions.base import EntityNotFound


def _to_response(rel) -> RelationshipResponse:
    """Convert Relationship model to response DTO."""
    return RelationshipResponse(
        id=rel.id,
        tenant_id=rel.tenant_id,
        source_entity_id=rel.source_entity_id,
        target_entity_id=rel.target_entity_id,
        relation_type=rel.relation_type,
        extra_data=rel.extra_data,
        created_at=rel.created_at,
        deleted_at=rel.deleted_at,
    )


class RelationshipService:
    """Domain service for Relationship operations.

    Rules:
    - Self-loop prevention (source != target)
    - Both entities must belong to the same tenant
    - Tenant isolation enforced
    """

    def __init__(self, uow: UnitOfWork):
        self._uow = uow

    async def create_relationship(
        self,
        data: RelationshipCreate,
        tenant_id: UUID,
    ) -> tuple[RelationshipResponse, RelationshipCreated]:
        """Create a relationship between two entities.

        Validates:
        - source_entity_id != target_entity_id (no self-loops)
        - Both entities exist in the tenant
        """
        if data.source_entity_id == data.target_entity_id:
            raise ValueError(
                "Self-loop not allowed: "
                "source_entity_id must differ from target_entity_id"
            )

        # Validate both entities exist and belong to the tenant
        source = await self._uow.entities.get_by_id(data.source_entity_id, tenant_id)
        if source is None:
            raise EntityNotFound(data.source_entity_id, "Entity")

        target = await self._uow.entities.get_by_id(data.target_entity_id, tenant_id)
        if target is None:
            raise EntityNotFound(data.target_entity_id, "Entity")

        rel = await self._uow.relationships.create_relation(
            tenant_id=tenant_id,
            source_entity_id=data.source_entity_id,
            target_entity_id=data.target_entity_id,
            relation_type=data.relation_type,
        )
        await self._uow.commit()

        event = RelationshipCreated(
            relationship_id=rel.id,
            source_entity_id=rel.source_entity_id,
            target_entity_id=rel.target_entity_id,
            relation_type=rel.relation_type,
            tenant_id=rel.tenant_id,
        )

        return _to_response(rel), event

    async def delete_relationship(
        self,
        relationship_id: UUID,
        tenant_id: UUID,
    ) -> bool:
        """Soft delete a relationship."""
        deleted = await self._uow.relationships.delete_relation(relationship_id, tenant_id)
        if deleted:
            await self._uow.commit()

            _ = RelationshipDeleted(
                relationship_id=relationship_id,
                tenant_id=tenant_id,
            )
            # Event would be dispatched here in production
        return deleted

    async def get_children(self, entity_id: UUID, tenant_id: UUID) -> list[RelationshipResponse]:
        """Get all entities that are children of the given entity (as source)."""
        relations = await self._uow.relationships.list_source_relations(entity_id, tenant_id)
        return [_to_response(r) for r in relations]

    async def get_parents(self, entity_id: UUID, tenant_id: UUID) -> list[RelationshipResponse]:
        """Get all entities that are parents of the given entity (as target)."""
        relations = await self._uow.relationships.list_target_relations(entity_id, tenant_id)
        return [_to_response(r) for r in relations]

    async def get_relationships_for_entity(
        self,
        entity_id: UUID,
        tenant_id: UUID,
    ) -> list[RelationshipResponse]:
        """Get all relationships involving an entity."""
        relations = await self._uow.relationships.get_relationships_for_entity(entity_id, tenant_id)
        return [_to_response(r) for r in relations]

    @property
    def events(self):
        return {
            "relationship_created": RelationshipCreated,
            "relationship_deleted": RelationshipDeleted,
        }
