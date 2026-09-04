"""Asset Repository - Manages Asset domain objects."""
from typing import Optional, Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from services.core.models.models import Asset
from services.core.repositories.base import TenantAwareRepository


class AssetRepository(TenantAwareRepository[Asset]):
    """Repository for Asset domain operations."""

    def __init__(self, session: AsyncSession):
        super().__init__(session, model=Asset)

    async def get_by_id(self, asset_id: UUID, tenant_id: Optional[UUID] = None) -> Optional[Asset]:
        """Get asset by ID."""
        stmt = select(Asset).where(Asset.id == asset_id)

        if tenant_id:
            stmt = stmt.where(Asset.tenant_id == tenant_id)

        stmt = stmt.where(Asset.deleted_at.is_(None))

        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_code(self, asset_code: str) -> Optional[Asset]:
        """Get asset by unique code."""
        stmt = select(Asset).where(
            Asset.asset_code == asset_code,
            Asset.deleted_at.is_(None)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_entity(self, entity_id: UUID) -> Optional[Asset]:
        """Get asset linked to an entity (1:1 relationship)."""
        stmt = select(Asset).where(
            Asset.entity_id == entity_id,
            Asset.deleted_at.is_(None)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_class(
        self,
        asset_class: str,
        tenant_id: Optional[UUID] = None,
        limit: int = 20,
        offset: int = 0
    ) -> Sequence[Asset]:
        """List assets by class."""
        stmt = (
            select(Asset)
            .where(Asset.asset_class == asset_class)
            .where(Asset.deleted_at.is_(None))
            .offset(offset)
            .limit(limit)
        )

        if tenant_id:
            stmt = stmt.where(Asset.tenant_id == tenant_id)

        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def create_asset(self, asset: Asset) -> Asset:
        """Create a new asset. Caller must commit transaction."""
        self.session.add(asset)
        await self.session.flush()
        await self.session.refresh(asset)
        return asset

    async def update(self, asset: Asset) -> Asset:
        """Update an existing asset. Caller must commit transaction."""
        await self.session.merge(asset)
        await self.session.flush()
        return asset

    async def soft_delete(self, asset_id: UUID, tenant_id: Optional[UUID] = None) -> bool:
        """Soft delete an asset."""
        asset = await self.get_by_id(asset_id, tenant_id)
        if asset is None:
            return False

        asset.soft_delete()
        await self.session.flush()
        return True

    # Backward compatibility aliases for service layer
    async def list_all(
        self,
        asset_class: Optional[str] = None,
        skip: int = 0,
        limit: int = 20
    ) -> Sequence[Asset]:
        """Alias for list_by_class (service layer compat)."""
        return await self.list_by_class(asset_class or "", limit, skip)
