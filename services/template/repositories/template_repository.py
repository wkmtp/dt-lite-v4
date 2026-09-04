"""Template repository — data access for twin_templates table."""
from typing import Optional, Sequence
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from services.core.repositories.base import TenantAwareRepository
from services.template.models import TwinTemplate


class TemplateRepository(TenantAwareRepository[TwinTemplate]):
    """Repository for TwinTemplate CRUD operations."""

    def __init__(self, session: AsyncSession):
        super().__init__(session, model=TwinTemplate)

    async def get_by_code(self, code: str, tenant_id: UUID) -> Optional[TwinTemplate]:
        """Get template by code within tenant scope."""
        stmt = select(TwinTemplate).where(
            TwinTemplate.code == code.lower(),
            TwinTemplate.tenant_id == tenant_id,
            TwinTemplate.deleted_at.is_(None),
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_active(self, tenant_id: UUID, limit: int = 100, offset: int = 0) -> Sequence[TwinTemplate]:
        """List active templates for tenant."""
        stmt = (
            select(TwinTemplate)
            .where(
                TwinTemplate.tenant_id == tenant_id,
                TwinTemplate.deleted_at.is_(None),
                TwinTemplate.status == "active",
            )
            .order_by(TwinTemplate.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def count_active(self, tenant_id: UUID) -> int:
        """Count active templates for tenant."""
        stmt = (
            select(func.count())
            .select_from(TwinTemplate)
            .where(
                TwinTemplate.tenant_id == tenant_id,
                TwinTemplate.deleted_at.is_(None),
                TwinTemplate.status == "active",
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()
