"""TwinGraphService — Business logic for twin graph operations.

Manages semantic relationships between twin entities and provides
graph traversal through TwinQueryEngine.
"""
import logging
from typing import Optional
from uuid import UUID

from services.twin_graph.exceptions import (
    InvalidRelationshipError,
    TwinEntityNotFoundError,
    TwinRelationshipNotFoundError,
)
from services.twin_graph.models import TwinRelationship
from services.twin_graph.query import TwinQueryEngine
from services.twin_graph.repositories import TwinRelationshipRepository
from services.twin.repositories.entity_repository import EntityRepository

logger = logging.getLogger(__name__)


class TwinGraphService:
    """Business logic layer for twin graph operations.

    Responsibilities:
    - Create/remove semantic relationships between twin entities
    - Validate that both endpoints exist and belong to the same tenant
    - Provide graph traversal through TwinQueryEngine
    """

    def __init__(self, session):
        self._session = session
        self._repo = TwinRelationshipRepository(session)
        self._entity_repo = EntityRepository(session)
        self._query_engine = TwinQueryEngine(self._repo)

    async def create_relation(
        self,
        source_id: UUID,
        target_id: UUID,
        relationship_type: str,
        tenant_id: UUID,
        metadata: Optional[dict] = None,
    ) -> TwinRelationship:
        """Create a new relationship between two twin entities.

        Validates:
        - Both source and target exist in the same tenant
        - Source and target are different entities (no self-loops)
        - No duplicate relationship already exists
        """
        if source_id == target_id:
            raise InvalidRelationshipError(
                f"Source and target must differ: {source_id}"
            )

        # Verify both entities exist and belong to this tenant
        source_entity = await self._entity_repo.get_by_id_for_tenant(source_id, tenant_id)
        if source_entity is None:
            raise TwinEntityNotFoundError(source_id)

        target_entity = await self._entity_repo.get_by_id_for_tenant(target_id, tenant_id)
        if target_entity is None:
            raise TwinEntityNotFoundError(target_id)

        # Check for duplicate
        existing = await self._repo.get_by_ids(source_id, target_id, tenant_id)
        if existing is not None:
            raise InvalidRelationshipError(
                f"Relationship already exists: {source_id} --[{relationship_type}]--> {target_id}"
            )

        rel = TwinRelationship(
            tenant_id=tenant_id,
            source_twin_id=source_id,
            target_twin_id=target_id,
            relationship_type=relationship_type,
            meta_data=metadata or {},
        )
        return await self._repo.create(rel)

    async def remove_relation(self, relationship_id: UUID, tenant_id: UUID) -> bool:
        """Remove a relationship (soft delete)."""
        rel = await self._repo.get_by_id_for_tenant(relationship_id, tenant_id)
        if rel is None:
            raise TwinRelationshipNotFoundError(relationship_id)
        return await self._repo.soft_delete(relationship_id)

    async def get_relation(self, relationship_id: UUID, tenant_id: UUID) -> TwinRelationship:
        """Get a relationship by ID with tenant verification."""
        rel = await self._repo.get_by_id_for_tenant(relationship_id, tenant_id)
        if rel is None:
            raise TwinRelationshipNotFoundError(relationship_id)
        return rel

    async def get_neighbors(
        self,
        twin_id: UUID,
        tenant_id: UUID,
        relationship_type: Optional[str] = None,
        direction: str = "both",
    ) -> list[dict]:
        """Get all neighboring twin entities."""
        # Verify entity exists in tenant
        entity = await self._entity_repo.get_by_id_for_tenant(twin_id, tenant_id)
        if entity is None:
            raise TwinEntityNotFoundError(twin_id)
        return await self._query_engine.get_neighbors(
            twin_id, tenant_id, relationship_type=relationship_type, direction=direction
        )

    async def find_path(
        self,
        source_id: UUID,
        target_id: UUID,
        tenant_id: UUID,
        max_depth: int = 5,
    ) -> Optional[list[dict]]:
        """Find a path between two twin entities via BFS."""
        # Verify both entities exist
        src = await self._entity_repo.get_by_id_for_tenant(source_id, tenant_id)
        if src is None:
            raise TwinEntityNotFoundError(source_id)
        tgt = await self._entity_repo.get_by_id_for_tenant(target_id, tenant_id)
        if tgt is None:
            raise TwinEntityNotFoundError(target_id)
        return await self._query_engine.find_path(source_id, target_id, tenant_id, max_depth)

    async def list_relations_by_type(
        self, relationship_type: str, tenant_id: UUID, limit: int = 100
    ) -> list[TwinRelationship]:
        """List all relationships of a given type within tenant."""
        return await self._repo.list_by_type(relationship_type, tenant_id, limit=limit)
