"""BindingService — Business logic for TwinBinding management."""
import logging
from typing import Optional
from uuid import UUID

from services.twin.exceptions import (
    TwinDeviceNotFoundError,
    TwinEntityNotFoundError,
    TwinBindingAlreadyExistsError,
)
from services.twin.models.binding import TwinBinding
from services.twin.repositories.binding_repository import BindingRepository
from services.iota.repositories.device_repository import DeviceRepository
from services.twin.repositories.entity_repository import EntityRepository

logger = logging.getLogger(__name__)


class BindingService:
    """Service for managing TwinBinding relationships."""

    def __init__(self, session):
        self._repo = BindingRepository(session)
        self._device_repo = DeviceRepository(session)
        self._entity_repo = EntityRepository(session)

    async def create(
        self,
        device_id: UUID,
        entity_id: UUID,
        tenant_id: UUID,
        binding_type: str = "mirror",
        metadata: Optional[dict] = None,
    ) -> TwinBinding:
        # Verify device exists and belongs to tenant
        device = await self._device_repo.get_by_id_for_tenant(device_id, tenant_id)
        if device is None:
            raise TwinDeviceNotFoundError(device_id)

        # Verify entity exists and belongs to tenant
        entity = await self._entity_repo.get_by_id_for_tenant(entity_id, tenant_id)
        if entity is None:
            raise TwinEntityNotFoundError(entity_id)

        # Check for existing binding
        existing = await self._repo.get_by_device(device_id, tenant_id)
        if existing is not None:
            raise TwinBindingAlreadyExistsError(device_id, entity_id)

        binding = TwinBinding(
            tenant_id=tenant_id,
            device_id=device_id,
            twin_entity_id=entity_id,
            binding_type=binding_type,
            meta_data=metadata or {},
        )

        return await self._repo.create(binding)

    async def delete(self, binding_id: UUID, tenant_id: UUID) -> bool:
        return await self._repo.soft_delete(binding_id)

    async def get_by_device(self, device_id: UUID, tenant_id: UUID) -> Optional[TwinBinding]:
        return await self._repo.get_by_device(device_id, tenant_id)

    async def list_by_entity(self, entity_id: UUID, tenant_id: UUID) -> list[TwinBinding]:
        return await self._repo.list_by_entity(entity_id, tenant_id)
