"""DataSource Service - Manages DataSource lifecycle."""
from typing import Optional
from uuid import UUID

from services.core.unit_of_work import UnitOfWork
from services.exceptions.base import ValidationError
from services.iota.models.models import DataSource


class DataSourceService:
    """Domain service for DataSource operations."""

    def __init__(self, uow: UnitOfWork):
        self._uow = uow

    async def create_data_source(
        self,
        name: str,
        data_type: str,
        config: dict,
        tenant_id: UUID,
        description: Optional[str] = None,
    ) -> DataSource:
        """Create a new DataSource."""
        # Validate type is not protocol-specific
        if any(proto in data_type.lower() for proto in ["bacnet", "modbus", "opcua", "mqtt"]):
            raise ValidationError("type", f"Invalid datasource type: {data_type}")

        repo = self._uow.data_sources
        existing = await repo.get_by_name(name, tenant_id)
        if existing:
            raise ValidationError("name", f"Datasource '{name}' already exists")

        ds = DataSource(
            tenant_id=tenant_id,
            name=name,
            description=description,
            type=data_type,
            config=config or {},
        )
        ds = await repo.create(ds)
        await self._uow.commit()
        return ds

    async def list_data_sources(
        self,
        tenant_id: UUID,
        skip: int = 0,
        limit: int = 20,
    ) -> dict:
        """List datasources for tenant."""
        repo = self._uow.data_sources
        items = await repo.list(tenant_id=tenant_id, limit=limit, offset=skip)
        return {"items": [self._to_response(ds) for ds in items], "total": len(items)}

    async def get_data_source(self, ds_id: UUID, tenant_id: UUID) -> Optional[DataSource]:
        """Get datasource by ID with tenant check."""
        repo = self._uow.data_sources
        ds = await repo.get_by_id_for_tenant(ds_id, tenant_id)
        return ds

    async def delete_data_source(self, ds_id: UUID, tenant_id: UUID) -> bool:
        """Soft delete a datasource."""
        repo = self._uow.data_sources
        # Verify existence and tenant before soft delete
        ds = await repo.get_by_id_for_tenant(ds_id, tenant_id)
        if ds is None:
            return False
        deleted = await repo.soft_delete(ds_id)
        if deleted:
            await self._uow.commit()
        return deleted

    @staticmethod
    def _to_response(ds: DataSource) -> dict:
        return {
            "id": str(ds.id),
            "name": ds.name,
            "description": ds.description,
            "type": ds.type,
            "status": ds.status,
            "created_at": ds.created_at.isoformat(),
            "updated_at": ds.updated_at.isoformat(),
        }
