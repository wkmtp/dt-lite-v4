"""DefinitionRepository — Data access for TwinDefinition."""
from typing import Optional, Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from services.core.repositories.base import TenantAwareRepository
from services.twin.models.definition import TwinDefinition


class DefinitionRepository(TenantAwareRepository[TwinDefinition]):
    """Repository for TwinDefinition persistence operations."""

    def __init__(self, session: AsyncSession):
        super().__init__(session, model=TwinDefinition)

    async def get_by_code(self, code: str, tenant_id: UUID) -> Optional[TwinDefinition]:
        """Get definition by code within tenant scope."""
        stmt = select(TwinDefinition).where(
            TwinDefinition.code == code,
            TwinDefinition.tenant_id == tenant_id,
            TwinDefinition.deleted_at.is_(None)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_tenant(self, tenant_id: UUID, limit: int = 100, offset: int = 0) -> Sequence[TwinDefinition]:
        """List all definitions for a tenant."""
        return await self.list(tenant_id=tenant_id, limit=limit, offset=offset)

    async def count_by_tenant(self, tenant_id: UUID) -> int:
        """Count definitions for a tenant."""
        return await self.count(tenant_id=tenant_id)
