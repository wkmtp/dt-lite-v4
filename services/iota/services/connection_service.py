"""Connection Service - Manages Connection lifecycle."""
from typing import Optional
from uuid import UUID

from services.core.unit_of_work import UnitOfWork
from services.exceptions.base import ValidationError
from services.iota.models.models import Connection


class ConnectionService:
    """Domain service for Connection operations."""

    def __init__(self, uow: UnitOfWork):
        self._uow = uow

    async def create_connection(
        self,
        data_source_id: UUID,
        name: str,
        endpoint: str,
        credentials_ref: str,
        tenant_id: UUID,
        timeout: int = 30,
        retry_policy: Optional[dict] = None,
        config: Optional[dict] = None,
    ) -> Connection:
        """Create a new Connection."""
        repo = self._uow.connections

        # Validate data source belongs to tenant
        ds = await self._uow.data_sources.get_by_id_for_tenant(data_source_id, tenant_id)
        if ds is None:
            raise ValidationError("data_source_id", "Datasource not found or access denied")

        existing = await repo.get_by_name(name, tenant_id)
        if existing:
            raise ValidationError("name", f"Connection '{name}' already exists")

        conn = Connection(
            tenant_id=tenant_id,
            data_source_id=data_source_id,
            name=name,
            endpoint=endpoint,
            credentials_ref=credentials_ref,
            timeout=timeout,
            retry_policy=retry_policy or {},
            config=config or {},
        )
        conn = await repo.create(conn)
        await self._uow.commit()
        return conn

    async def list_connections(self, tenant_id: UUID, skip: int = 0, limit: int = 20) -> dict:
        """List connections for tenant."""
        repo = self._uow.connections
        items = await repo.list(tenant_id=tenant_id, limit=limit, offset=skip)
        return {"items": [self._to_response(c) for c in items], "total": len(items)}

    async def get_connection(self, conn_id: UUID, tenant_id: UUID) -> Optional[Connection]:
        """Get connection by ID with tenant check."""
        repo = self._uow.connections
        return await repo.get_by_id_for_tenant(conn_id, tenant_id)

    async def delete_connection(self, conn_id: UUID, tenant_id: UUID) -> bool:
        """Soft delete a connection."""
        repo = self._uow.connections
        # Verify existence and tenant before soft delete
        conn = await repo.get_by_id_for_tenant(conn_id, tenant_id)
        if conn is None:
            return False
        deleted = await repo.soft_delete(conn_id)
        if deleted:
            await self._uow.commit()
        return deleted

    @staticmethod
    def _to_response(conn: Connection) -> dict:
        return {
            "id": str(conn.id),
            "data_source_id": str(conn.data_source_id),
            "name": conn.name,
            # endpoint redaction is a response-layer security policy,
            # not a persistence-layer requirement.
            "endpoint": "<REDACTED>",
            "credentials_ref": conn.credentials_ref,
            "timeout": conn.timeout,
            "status": conn.status,
            "created_at": conn.created_at.isoformat(),
            "updated_at": conn.updated_at.isoformat(),
        }
