"""EntityService — Business logic for PersistentTwinEntity management."""
import logging
from typing import Optional
from uuid import UUID

from services.twin.exceptions import (
    TwinEntityNotFoundError,
)
from services.twin.models.entity import PersistentTwinEntity
from services.twin.repositories.entity_repository import EntityRepository

logger = logging.getLogger(__name__)


class EntityService:
    """Service for managing PersistentTwinEntity instances."""

    def __init__(self, session):
        self._repo = EntityRepository(session)

    async def create(
        self,
        external_id: str,
        name: str,
        definition_id: UUID,
        tenant_id: UUID,
        metadata: Optional[dict] = None,
    ) -> PersistentTwinEntity:
        entity = PersistentTwinEntity(
            tenant_id=tenant_id,
            definition_id=definition_id,
            external_id=external_id,
            name=name,
            meta_data=metadata or {},
        )
        return await self._repo.create(entity)

    async def get(self, entity_id: UUID, tenant_id: UUID) -> PersistentTwinEntity:
        entity = await self._repo.get_by_id_for_tenant(entity_id, tenant_id)
        if entity is None:
            raise TwinEntityNotFoundError(entity_id)
        return entity

    async def update_metadata(
        self,
        entity_id: UUID,
        tenant_id: UUID,
        metadata: dict,
    ) -> PersistentTwinEntity:
        entity = await self._repo.get_by_id_for_tenant(entity_id, tenant_id)
        if entity is None:
            raise TwinEntityNotFoundError(entity_id)
        entity.meta_data = metadata
        return await self._repo.update(entity)

    async def delete(self, entity_id: UUID, tenant_id: UUID) -> bool:
        return await self._repo.soft_delete(entity_id)

    async def list(
        self,
        tenant_id: UUID,
        limit: int = 100,
        offset: int = 0,
    ) -> list[PersistentTwinEntity]:
        return await self._repo.list(tenant_id=tenant_id, limit=limit, offset=offset)

    async def count(self, tenant_id: UUID) -> int:
        return await self._repo.count(tenant_id=tenant_id)
