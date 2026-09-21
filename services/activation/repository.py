"""Activation layer repositories."""
from typing import Optional, Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from services.core.repositories.base import TenantAwareRepository
from services.activation.models import TwinActivationLog, TwinCommand


class TwinActivationLogRepository(TenantAwareRepository[TwinActivationLog]):
    """Repository for activation log persistence."""

    def __init__(self, session: AsyncSession):
        super().__init__(session, model=TwinActivationLog)

    async def get_by_entity_for_tenant(
        self, entity_id: UUID, tenant_id: UUID,
    ) -> Optional[TwinActivationLog]:
        """Get activation log for a specific entity within tenant scope."""
        stmt = select(TwinActivationLog).where(
            TwinActivationLog.twin_entity_id == entity_id,
            TwinActivationLog.tenant_id == tenant_id,
            TwinActivationLog.deleted_at.is_(None),
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_state(
        self, state: str, tenant_id: UUID, limit: int = 100, offset: int = 0,
    ) -> Sequence[TwinActivationLog]:
        """List activation logs filtered by state within tenant."""
        stmt = (
            select(TwinActivationLog)
            .where(
                TwinActivationLog.tenant_id == tenant_id,
                TwinActivationLog.state == state,
                TwinActivationLog.deleted_at.is_(None),
            )
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()


class TwinCommandRepository(TenantAwareRepository[TwinCommand]):
    """Repository for command persistence."""

    def __init__(self, session: AsyncSession):
        super().__init__(session, model=TwinCommand)

    async def list_by_binding(
        self, binding_id: UUID, tenant_id: UUID, limit: int = 100, offset: int = 0,
    ) -> Sequence[TwinCommand]:
        """List commands for a binding within tenant scope."""
        stmt = (
            select(TwinCommand)
            .where(
                TwinCommand.twin_binding_id == binding_id,
                TwinCommand.tenant_id == tenant_id,
                TwinCommand.deleted_at.is_(None),
            )
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def list_by_status(
        self, status: str, tenant_id: UUID, limit: int = 100, offset: int = 0,
    ) -> Sequence[TwinCommand]:
        """List commands filtered by status within tenant."""
        stmt = (
            select(TwinCommand)
            .where(
                TwinCommand.tenant_id == tenant_id,
                TwinCommand.status == status,
                TwinCommand.deleted_at.is_(None),
            )
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()
