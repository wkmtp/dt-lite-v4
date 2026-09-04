"""Connection Repository - Manages Connection domain objects."""
from typing import Optional, Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from services.core.repositories.base import TenantAwareRepository
from services.iota.models.models import Connection


class ConnectionRepository(TenantAwareRepository[Connection]):
    """Repository for Connection domain operations."""

    def __init__(self, session: AsyncSession):
        super().__init__(session, model=Connection)

    async def get_by_data_source(self, data_source_id: UUID, tenant_id: UUID) -> Sequence[Connection]:
        """Get all connections for a data source within tenant."""
        stmt = select(Connection).where(
            Connection.data_source_id == data_source_id,
            Connection.tenant_id == tenant_id,
            Connection.deleted_at.is_(None)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_by_id_with_tenant_check(self, connection_id: UUID, tenant_id: UUID) -> Optional[Connection]:
        """Get connection by ID with tenant verification."""
        stmt = select(Connection).where(
            Connection.id == connection_id,
            Connection.tenant_id == tenant_id,
            Connection.deleted_at.is_(None)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
