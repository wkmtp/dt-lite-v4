"""Tenant Repository - Manages Tenant domain objects."""
from typing import Optional, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from services.core.repositories.base import BaseRepository
from services.identity.models.models import Tenant


class TenantRepository(BaseRepository[Tenant]):
    """Repository for Tenant domain operations."""

    def __init__(self, session: AsyncSession):
        super().__init__(session)
        self.model = Tenant

    async def get_by_code(self, code: str) -> Optional[Tenant]:
        """Get tenant by unique code."""
        stmt = select(Tenant).where(
            Tenant.code == code,
            Tenant.deleted_at.is_(None)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_id(self, tenant_id) -> Optional[Tenant]:
        """Get tenant by ID."""
        stmt = select(Tenant).where(Tenant.id == tenant_id, Tenant.deleted_at.is_(None))
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_active_tenants(self, limit: int = 20, offset: int = 0) -> Sequence[Tenant]:
        """List active tenants."""
        stmt = select(Tenant).where(
            Tenant.status == "active",
            Tenant.deleted_at.is_(None)
        ).offset(offset).limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def create(self, tenant: Tenant) -> Tenant:
        """Create a new tenant. Caller must commit."""
        self.session.add(tenant)
        await self.session.flush()
        await self.session.refresh(tenant)
        return tenant
