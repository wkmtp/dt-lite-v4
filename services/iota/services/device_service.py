"""Device Service - Manages Device lifecycle."""
from typing import Optional
from uuid import UUID

from services.core.unit_of_work import UnitOfWork
from services.exceptions.base import ValidationError
from services.iota.models.models import Device


class DeviceService:
    """Domain service for Device operations."""

    def __init__(self, uow: UnitOfWork):
        self._uow = uow

    async def create_device(
        self,
        external_id: str,
        name: str,
        device_type: str,
        tenant_id: UUID,
        data_source_id: Optional[UUID] = None,
        connection_id: Optional[UUID] = None,
        extra_data: Optional[dict] = None,
    ) -> Device:
        """Create a new Device."""
        repo = self._uow.devices

        existing = await repo.get_by_external_id(external_id, tenant_id)
        if existing:
            raise ValidationError("external_id", f"Device '{external_id}' already exists")

        # Validate references belong to tenant
        if data_source_id:
            ds = await self._uow.data_sources.get_by_id_for_tenant(data_source_id, tenant_id)
            if ds is None:
                raise ValidationError("data_source_id", "Datasource not found or access denied")

        if connection_id:
            conn = await self._uow.connections.get_by_id_for_tenant(connection_id, tenant_id)
            if conn is None:
                raise ValidationError("connection_id", "Connection not found or access denied")

        device = Device(
            tenant_id=tenant_id,
            data_source_id=data_source_id,
            connection_id=connection_id,
            external_id=external_id,
            name=name,
            device_type=device_type,
            extra_data=extra_data or {},
        )
        device = await repo.create(device)
        await self._uow.commit()
        return device

    async def list_devices(self, tenant_id: UUID, skip: int = 0, limit: int = 20) -> dict:
        """List devices for tenant."""
        repo = self._uow.devices
        items = await repo.list(tenant_id=tenant_id, limit=limit, offset=skip)
        return {"items": [self._to_response(d) for d in items], "total": len(items)}

    async def get_device(self, device_id: UUID, tenant_id: UUID) -> Optional[Device]:
        """Get device by ID with tenant check."""
        repo = self._uow.devices
        return await repo.get_by_id_for_tenant(device_id, tenant_id)

    async def delete_device(self, device_id: UUID, tenant_id: UUID) -> bool:
        """Soft delete a device."""
        repo = self._uow.devices
        # Verify existence and tenant before soft delete
        device = await repo.get_by_id_for_tenant(device_id, tenant_id)
        if device is None:
            return False
        deleted = await repo.soft_delete(device_id)
        if deleted:
            await self._uow.commit()
        return deleted

    @staticmethod
    def _to_response(device: Device) -> dict:
        return {
            "id": str(device.id),
            "tenant_id": str(device.tenant_id),
            "data_source_id": str(device.data_source_id) if device.data_source_id else None,
            "connection_id": str(device.connection_id) if device.connection_id else None,
            "external_id": device.external_id,
            "name": device.name,
            "device_type": device.device_type,
            "status": device.status,
            "metadata": device.extra_data,
            "created_at": device.created_at.isoformat(),
            "updated_at": device.updated_at.isoformat(),
        }
