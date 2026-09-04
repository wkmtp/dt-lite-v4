"""Device-Twin Binding Service - Manages Device <-> Entity bindings."""
from typing import Optional
from uuid import UUID

from services.core.unit_of_work import UnitOfWork
from services.exceptions.base import ValidationError
from services.iota.models.models import DeviceEntityBinding


class DeviceEntityBindingService:
    """Domain service for Device-Entity binding operations."""

    def __init__(self, uow: UnitOfWork):
        self._uow = uow

    async def create_binding(
        self,
        device_id: UUID,
        entity_id: UUID,
        binding_type: str,
        tenant_id: UUID,
        metadata: Optional[dict] = None,
    ) -> DeviceEntityBinding:
        """Create a binding between Device and Core Entity."""
        repo = self._uow.bindings

        # Verify device belongs to tenant
        device = await self._uow.devices.get_by_id_for_tenant(device_id, tenant_id)
        if device is None:
            raise ValidationError("device_id", "Device not found or access denied")

        # Verify entity belongs to tenant (Core service)
        entity = await self._uow.entities.get_by_id(entity_id)
        if entity is None or entity.tenant_id != tenant_id:
            raise ValidationError("entity_id", "Entity not found or access denied")

        # Check for existing binding
        if await repo.exists(device_id, entity_id, tenant_id):
            raise ValidationError("binding", "Binding already exists")

        binding = DeviceEntityBinding(
            tenant_id=tenant_id,
            device_id=device_id,
            entity_id=entity_id,
            binding_type=binding_type,
            extra_data=metadata or {},
        )
        binding = await repo.create(binding)
        await self._uow.commit()
        return binding

    async def list_bindings(self, tenant_id: UUID, skip: int = 0, limit: int = 20) -> dict:
        """List bindings for tenant."""
        repo = self._uow.bindings
        items = await repo.list(tenant_id=tenant_id, limit=limit, offset=skip)
        return {"items": [self._to_response(b) for b in items], "total": len(items)}

    async def delete_binding(self, binding_id: UUID, tenant_id: UUID) -> bool:
        """Soft delete a binding."""
        repo = self._uow.bindings
        deleted = await repo.soft_delete(binding_id)
        if deleted:
            await self._uow.commit()
        return deleted

    @staticmethod
    def _to_response(binding: DeviceEntityBinding) -> dict:
        return {
            "id": str(binding.id),
            "tenant_id": str(binding.tenant_id),
            "device_id": str(binding.device_id),
            "entity_id": str(binding.entity_id),
            "binding_type": binding.binding_type,
            "metadata": binding.extra_data,
            "created_at": binding.created_at.isoformat(),
            "updated_at": binding.updated_at.isoformat(),
        }
