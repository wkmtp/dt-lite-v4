"""Deployment instance repository."""
from typing import Optional, Sequence
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from services.core.repositories.base import TenantAwareRepository
from services.deployment.models import DeploymentInstance


class DeploymentInstanceRepository(TenantAwareRepository[DeploymentInstance]):
    """Repository for deployment instance queries."""

    def __init__(self, session: AsyncSession):
        super().__init__(session, model=DeploymentInstance)

    async def get_by_id_for_tenant(
        self, instance_id: UUID, tenant_id: UUID
    ) -> Optional[DeploymentInstance]:
        """Get instance by ID with tenant isolation."""
        stmt = select(DeploymentInstance).where(
            DeploymentInstance.id == instance_id,
            DeploymentInstance.tenant_id == tenant_id,
            DeploymentInstance.deleted_at.is_(None),
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_name(
        self, name: str, tenant_id: UUID
    ) -> Optional[DeploymentInstance]:
        """Get instance by name within tenant scope."""
        stmt = select(DeploymentInstance).where(
            DeploymentInstance.name == name.strip(),
            DeploymentInstance.tenant_id == tenant_id,
            DeploymentInstance.deleted_at.is_(None),
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_profile(
        self, profile_id: UUID, tenant_id: UUID
    ) -> Sequence[DeploymentInstance]:
        """List instances for a specific profile."""
        stmt = select(DeploymentInstance).where(
            DeploymentInstance.profile_id == profile_id,
            DeploymentInstance.tenant_id == tenant_id,
            DeploymentInstance.deleted_at.is_(None),
        ).order_by(DeploymentInstance.name)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def count_active(self, tenant_id: UUID) -> int:
        """Count active instances for tenant."""
        stmt = select(func.count()).select_from(DeploymentInstance).where(
            DeploymentInstance.tenant_id == tenant_id,
            DeploymentInstance.deleted_at.is_(None),
            DeploymentInstance.status.in_(["ready", "deployed", "running"]),
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def update_status(
        self, instance_id: UUID, new_status: str, tenant_id: UUID
    ) -> Optional[DeploymentInstance]:
        """Update instance status with tenant verification."""
        stmt = select(DeploymentInstance).where(
            DeploymentInstance.id == instance_id,
            DeploymentInstance.tenant_id == tenant_id,
            DeploymentInstance.deleted_at.is_(None),
        )
        result = await self.session.execute(stmt)
        instance = result.scalar_one_or_none()
        if instance:
            instance.status = new_status
            await self.session.flush()
        return instance
