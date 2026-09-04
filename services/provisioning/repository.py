"""Provisioning repositories."""
from typing import Optional, Sequence
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from services.core.repositories.base import TenantAwareRepository
from services.provisioning.models import ProvisioningExecution, ProvisioningItem, ProvisioningPlan


class ProvisioningPlanRepository(TenantAwareRepository[ProvisioningPlan]):
    """Repository for provisioning plan queries."""

    def __init__(self, session: AsyncSession):
        super().__init__(session, model=ProvisioningPlan)

    async def get_by_deployment_id(
        self, deployment_instance_id: UUID, tenant_id: UUID
    ) -> Optional[ProvisioningPlan]:
        """Get existing plan for a deployment instance (idempotency check)."""
        stmt = select(ProvisioningPlan).where(
            ProvisioningPlan.deployment_instance_id == deployment_instance_id,
            ProvisioningPlan.tenant_id == tenant_id,
            ProvisioningPlan.deleted_at.is_(None),
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def count_active(self, tenant_id: UUID) -> int:
        """Count active plans."""
        stmt = select(func.count()).select_from(ProvisioningPlan).where(
            ProvisioningPlan.tenant_id == tenant_id,
            ProvisioningPlan.deleted_at.is_(None),
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()


class ProvisioningItemRepository(TenantAwareRepository[ProvisioningItem]):
    """Repository for provisioning item queries."""

    def __init__(self, session: AsyncSession):
        super().__init__(session, model=ProvisioningItem)

    async def list_by_plan(self, plan_id: UUID, tenant_id: UUID) -> Sequence[ProvisioningItem]:
        """List all items for a plan."""
        stmt = select(ProvisioningItem).where(
            ProvisioningItem.plan_id == plan_id,
            ProvisioningItem.tenant_id == tenant_id,
            ProvisioningItem.deleted_at.is_(None),
        ).order_by(ProvisioningItem.id)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def count_by_status(self, plan_id: UUID, status: str, tenant_id: UUID) -> int:
        """Count items by status."""
        stmt = select(func.count()).select_from(ProvisioningItem).where(
            ProvisioningItem.plan_id == plan_id,
            ProvisioningItem.status == status,
            ProvisioningItem.tenant_id == tenant_id,
            ProvisioningItem.deleted_at.is_(None),
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def get_by_external_id(self, external_id: str, tenant_id: UUID) -> Optional[ProvisioningItem]:
        """Check idempotency - find existing item with same external_id."""
        stmt = select(ProvisioningItem).where(
            ProvisioningItem.external_id == external_id,
            ProvisioningItem.tenant_id == tenant_id,
            ProvisioningItem.status.in_(["pending", "completed"]),
            ProvisioningItem.deleted_at.is_(None),
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def update_status(self, item_id: UUID, new_status: str, tenant_id: UUID) -> Optional[ProvisioningItem]:
        """Update item status."""
        stmt = select(ProvisioningItem).where(
            ProvisioningItem.id == item_id,
            ProvisioningItem.tenant_id == tenant_id,
            ProvisioningItem.deleted_at.is_(None),
        )
        result = await self.session.execute(stmt)
        item = result.scalar_one_or_none()
        if item:
            item.status = new_status
            await self.session.flush()
        return item


class ProvisioningExecutionRepository(TenantAwareRepository[ProvisioningExecution]):
    """Repository for provisioning execution queries."""

    def __init__(self, session: AsyncSession):
        super().__init__(session, model=ProvisioningExecution)

    async def list_by_plan(self, plan_id: UUID, tenant_id: UUID) -> Sequence[ProvisioningExecution]:
        """List executions for a plan."""
        stmt = select(ProvisioningExecution).where(
            ProvisioningExecution.plan_id == plan_id,
            ProvisioningExecution.tenant_id == tenant_id,
            ProvisioningExecution.deleted_at.is_(None),
        ).order_by(ProvisioningExecution.started_at.desc())
        result = await self.session.execute(stmt)
        return result.scalars().all()
