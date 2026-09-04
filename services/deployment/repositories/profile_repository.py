"""Deployment profile repository."""
from typing import Optional, Sequence
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from services.core.repositories.base import TenantAwareRepository
from services.deployment.models import DeploymentProfile


class DeploymentProfileRepository(TenantAwareRepository[DeploymentProfile]):
    """Repository for deployment profile queries."""

    def __init__(self, session: AsyncSession):
        super().__init__(session, model=DeploymentProfile)

    async def get_by_id_for_tenant(
        self, profile_id: UUID, tenant_id: UUID
    ) -> Optional[DeploymentProfile]:
        """Get profile by ID with tenant isolation."""
        stmt = select(DeploymentProfile).where(
            DeploymentProfile.id == profile_id,
            DeploymentProfile.tenant_id == tenant_id,
            DeploymentProfile.deleted_at.is_(None),
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_name(
        self, name: str, tenant_id: UUID
    ) -> Optional[DeploymentProfile]:
        """Get profile by name within tenant scope."""
        stmt = select(DeploymentProfile).where(
            DeploymentProfile.name == name.strip(),
            DeploymentProfile.tenant_id == tenant_id,
            DeploymentProfile.deleted_at.is_(None),
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def count_active(self, tenant_id: UUID) -> int:
        """Count active profiles for tenant."""
        stmt = select(func.count()).select_from(DeploymentProfile).where(
            DeploymentProfile.tenant_id == tenant_id,
            DeploymentProfile.deleted_at.is_(None),
            DeploymentProfile.status.in_(["draft", "active"]),
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def list_by_template(
        self, template_id: UUID, tenant_id: UUID
    ) -> Sequence[DeploymentProfile]:
        """List profiles linked to a specific template."""
        stmt = select(DeploymentProfile).where(
            DeploymentProfile.template_id == template_id,
            DeploymentProfile.tenant_id == tenant_id,
            DeploymentProfile.deleted_at.is_(None),
        ).order_by(DeploymentProfile.name)
        result = await self.session.execute(stmt)
        return result.scalars().all()
