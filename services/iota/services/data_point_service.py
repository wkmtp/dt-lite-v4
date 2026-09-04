"""DataPoint Service - Manages DataPoint lifecycle."""
from typing import Optional
from uuid import UUID

from services.core.unit_of_work import UnitOfWork
from services.exceptions.base import ValidationError
from services.iota.models.models import DataPoint


class DataPointService:
    """Domain service for DataPoint operations."""

    def __init__(self, uow: UnitOfWork):
        self._uow = uow

    async def create_data_point(
        self,
        device_id: UUID,
        external_id: str,
        key: str,
        name: str,
        data_type: str,
        access_mode: str,
        sampling_mode: str,
        tenant_id: UUID,
        unit: Optional[str] = None,
        extra_data: Optional[dict] = None,
    ) -> DataPoint:
        """Create a new DataPoint."""
        repo = self._uow.data_points

        # Verify device belongs to tenant
        device = await self._uow.devices.get_by_id_for_tenant(device_id, tenant_id)
        if device is None:
            raise ValidationError("device_id", "Device not found or access denied")

        # Validate access_mode
        if access_mode not in ("READ", "WRITE", "READ_WRITE"):
            raise ValidationError("access_mode", f"Invalid access mode: {access_mode}")

        point = DataPoint(
            tenant_id=tenant_id,
            device_id=device_id,
            external_id=external_id,
            key=key,
            name=name,
            data_type=data_type,
            unit=unit,
            access_mode=access_mode,
            sampling_mode=sampling_mode,
            extra_data=extra_data or {},
        )
        point = await repo.create(point)
        await self._uow.commit()
        return point

    async def list_data_points(self, tenant_id: UUID, skip: int = 0, limit: int = 20) -> dict:
        """List data points for tenant."""
        repo = self._uow.data_points
        items = await repo.list(tenant_id=tenant_id, limit=limit, offset=skip)
        return {"items": [self._to_response(dp) for dp in items], "total": len(items)}

    async def get_data_point(self, dp_id: UUID, tenant_id: UUID) -> Optional[dict]:
        """Get data point by ID with tenant check."""
        repo = self._uow.data_points
        point = await repo.get_by_id_for_tenant(dp_id, tenant_id)
        if point is not None:
            return self._to_response(point)
        return None

    async def delete_data_point(self, dp_id: UUID, tenant_id: UUID) -> bool:
        """Soft delete a data point."""
        repo = self._uow.data_points
        # Verify existence and tenant before soft delete
        point = await repo.get_by_id_for_tenant(dp_id, tenant_id)
        if point is None:
            return False
        deleted = await repo.soft_delete(dp_id)
        if deleted:
            await self._uow.commit()
        return deleted

    @staticmethod
    def _to_response(point) -> dict:
        return {
            "id": str(point.id),
            "tenant_id": str(point.tenant_id),
            "device_id": str(point.device_id),
            "external_id": point.external_id,
            "key": point.key,
            "name": point.name,
            "data_type": point.data_type,
            "unit": point.unit,
            "access_mode": point.access_mode,
            "sampling_mode": point.sampling_mode,
            "metadata": point.extra_data,
            "created_at": point.created_at.isoformat(),
            "updated_at": point.updated_at.isoformat(),
        }
