"""Deployment node repository."""
from typing import Optional, Sequence
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from services.core.repositories.base import TenantAwareRepository
from services.deployment.models import DeploymentNode


class DeploymentNodeRepository(TenantAwareRepository[DeploymentNode]):
    """Repository for deployment node queries."""

    def __init__(self, session: AsyncSession):
        super().__init__(session, model=DeploymentNode)

    async def get_by_id_for_tenant(
        self, node_id: UUID, tenant_id: UUID
    ) -> Optional[DeploymentNode]:
        """Get node by ID with tenant isolation."""
        stmt = select(DeploymentNode).where(
            DeploymentNode.id == node_id,
            DeploymentNode.tenant_id == tenant_id,
            DeploymentNode.deleted_at.is_(None),
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_deployment(
        self, deployment_id: UUID, tenant_id: UUID
    ) -> Sequence[DeploymentNode]:
        """List nodes for a specific deployment instance."""
        stmt = select(DeploymentNode).where(
            DeploymentNode.deployment_id == deployment_id,
            DeploymentNode.tenant_id == tenant_id,
            DeploymentNode.deleted_at.is_(None),
        ).order_by(DeploymentNode.name)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def count_by_deployment(self, deployment_id: UUID) -> int:
        """Count nodes for a deployment instance."""
        stmt = select(func.count()).select_from(DeploymentNode).where(
            DeploymentNode.deployment_id == deployment_id,
            DeploymentNode.deleted_at.is_(None),
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()
