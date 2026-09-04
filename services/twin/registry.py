"""TwinEntityRegistry — In-memory runtime registry for TwinEntities.

This is a pure in-memory registry. It does NOT:
  - Connect to any database
  - Use SQLAlchemy
  - Implement persistence
  - Handle tenant isolation at the storage level (calls must be tenant-scoped)

Usage:
  All operations MUST pass tenant_id from TenantContext.
  The registry enforces tenant isolation at the method level.
"""
import logging
from typing import List, Optional
from uuid import UUID

from services.twin.exceptions import TwinEntityAlreadyExistsError
from services.twin.models import TwinEntity

logger = logging.getLogger(__name__)


class TwinEntityRegistry:
    """In-memory runtime registry for TwinEntity objects.

    This registry maintains the current set of active twin entities
    for all tenants. Each entity is scoped to its tenant.

    Thread-safety note: This implementation uses simple dict locking.
    For production concurrent access, consider adding asyncio.Lock
    or using an async-safe collection.
    """

    def __init__(self) -> None:
        # Internal storage: {tenant_id: {entity_id: TwinEntity}}
        self._storage: dict[UUID, dict[UUID, TwinEntity]] = {}

    def register(self, entity: TwinEntity) -> TwinEntity:
        """Register a new twin entity.

        Args:
            entity: TwinEntity to register. Must have a valid tenant_id.

        Returns:
            The registered TwinEntity (with ID populated).

        Raises:
            TwinEntityAlreadyExistsError: If entity with same ID exists for this tenant.
        """
        if not entity.id:
            raise ValueError("TwinEntity must have a valid id")

        tenant_id = entity.tenant_id
        if tenant_id not in self._storage:
            self._storage[tenant_id] = {}

        if entity.id in self._storage[tenant_id]:
            raise TwinEntityAlreadyExistsError(entity.id)

        self._storage[tenant_id][entity.id] = entity
        logger.info(
            "Registered TwinEntity: id=%s tenant=%s name=%s type=%s",
            entity.id,
            tenant_id,
            entity.name,
            entity.entity_type,
        )
        return entity

    def get(self, entity_id: UUID, tenant_id: UUID) -> Optional[TwinEntity]:
        """Get a twin entity by ID and tenant.

        Args:
            entity_id: The entity ID to look up.
            tenant_id: The tenant scope (must match entity's tenant).

        Returns:
            The TwinEntity if found and tenant matches, otherwise None.
        """
        tenant_entities = self._storage.get(tenant_id, {})
        entity = tenant_entities.get(entity_id)

        # Verify tenant ownership (defense in depth)
        if entity and entity.tenant_id != tenant_id:
            logger.warning(
                "Tenant mismatch attempt: entity=%s requested_by=%s actual=%s",
                entity_id,
                tenant_id,
                entity.tenant_id,
            )
            return None

        return entity

    def remove(self, entity_id: UUID, tenant_id: UUID) -> bool:
        """Remove a twin entity.

        Args:
            entity_id: The entity ID to remove.
            tenant_id: The tenant scope.

        Returns:
            True if removed, False if not found.
        """
        tenant_entities = self._storage.get(tenant_id, {})
        if entity_id in tenant_entities:
            del tenant_entities[entity_id]
            logger.info("Removed TwinEntity: id=%s tenant=%s", entity_id, tenant_id)
            return True
        return False

    def list(self, tenant_id: UUID, limit: int = 100, offset: int = 0) -> List[TwinEntity]:
        """List twin entities for a tenant with pagination.

        Args:
            tenant_id: The tenant scope.
            limit: Maximum number of entities to return.
            offset: Pagination offset.

        Returns:
            List of TwinEntity objects for the tenant.
        """
        tenant_entities = self._storage.get(tenant_id, {})
        entities = list(tenant_entities.values())
        # Sort by created_at descending for consistent ordering
        entities.sort(key=lambda e: e.created_at, reverse=True)
        return entities[offset: offset + limit]

    def contains(self, entity_id: UUID, tenant_id: UUID) -> bool:
        """Check if an entity exists for a tenant.

        Args:
            entity_id: The entity ID to check.
            tenant_id: The tenant scope.

        Returns:
            True if the entity exists, False otherwise.
        """
        return self.get(entity_id, tenant_id) is not None

    def count(self, tenant_id: UUID) -> int:
        """Count the number of twin entities for a tenant.

        Args:
            tenant_id: The tenant scope.

        Returns:
            Number of entities for this tenant.
        """
        return len(self._storage.get(tenant_id, {}))

    def clear(self, tenant_id: UUID) -> int:
        """Clear all entities for a tenant.

        Args:
            tenant_id: The tenant scope.

        Returns:
            Number of entities cleared.
        """
        count = len(self._storage.get(tenant_id, {}))
        self._storage.pop(tenant_id, None)
        logger.info("Cleared %d TwinEntities for tenant=%s", count, tenant_id)
        return count
