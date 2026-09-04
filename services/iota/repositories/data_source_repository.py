"""DataSource Repository - Manages DataSource domain objects."""
from typing import Optional, Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from services.core.repositories.base import TenantAwareRepository
from services.iota.models.models import DataSource


class DataSourceRepository(TenantAwareRepository[DataSource]):
    """Repository for DataSource domain operations."""

    def __init__(self, session: AsyncSession):
        super().__init__(session, model=DataSource)

    async def get_by_name(self, name: str, tenant_id: UUID) -> Optional[DataSource]:
        """Get datasource by name within a tenant."""
        stmt = select(DataSource).where(
            DataSource.name == name,
            DataSource.tenant_id == tenant_id,
            DataSource.deleted_at.is_(None)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_active(self, tenant_id: UUID, limit: int = 20, offset: int = 0) -> Sequence[DataSource]:
        """List active datasources within a tenant."""
        stmt = select(DataSource).where(
            DataSource.tenant_id == tenant_id,
            DataSource.status == "active",
            DataSource.deleted_at.is_(None)
        ).offset(offset).limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()
