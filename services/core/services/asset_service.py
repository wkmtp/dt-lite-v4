"""Asset Service - Domain application service for Asset lifecycle.

Responsible for:
- Asset creation with entity binding validation
- Asset lifecycle management
- Preventing orphan assets (must be bound to an entity)
- Domain event preparation
"""
from typing import Optional
from uuid import UUID

from services.core.models.models import Asset
from services.core.schemas.asset import (
    AssetCreate,
    AssetListResponse,
    AssetResponse,
)
from services.core.unit_of_work import UnitOfWork
from services.events.domain_events import AssetBound, AssetCreated, AssetUnbound
from services.exceptions.base import EntityNotFound


def _to_response(asset: Asset) -> AssetResponse:
    """Convert Asset model to response DTO."""
    return AssetResponse(
        id=asset.id,
        entity_id=asset.entity_id,
        asset_code=asset.asset_code,
        asset_class=asset.asset_class,
        lifecycle_status=asset.lifecycle_status,
        manufacturer=asset.manufacturer,
        model=asset.model,
        serial_number=asset.serial_number,
        installed_at=asset.installed_at,
        extra_data=asset.extra_data,
        created_at=asset.created_at,
        updated_at=asset.updated_at,
        deleted_at=asset.deleted_at,
    )


class AssetService:
    """Domain service for Asset operations.

    Rules:
    - Asset must be bound to an Entity (no orphan assets)
    - Asset code must be unique
    """

    def __init__(self, uow: UnitOfWork):
        self._uow = uow

    async def create_asset(
        self, data: AssetCreate, tenant_id: UUID
    ) -> tuple[AssetResponse, AssetCreated]:
        """Create a new asset bound to an entity.

        Validates:
        - Entity exists and belongs to tenant
        - Asset code is unique
        """
        # Validate entity exists
        entity = await self._uow.entities.get_by_id(data.entity_id, tenant_id)
        if entity is None:
            raise EntityNotFound(data.entity_id, "Entity")

        # Check duplicate asset code
        existing = await self._uow.assets.get_by_code(data.asset_code)
        if existing is not None:
            from services.exceptions.base import AssetAlreadyExists
            raise AssetAlreadyExists(data.asset_code)

        asset = Asset(
            entity_id=data.entity_id,
            asset_code=data.asset_code.strip(),
            asset_class=data.asset_class.strip(),
            manufacturer=data.manufacturer,
            model=data.model,
            serial_number=data.serial_number,
            installed_at=data.installed_at,
            extra_data=data.extra_data,
        )

        asset = await self._uow.assets.create_asset(asset)
        await self._uow.commit()

        event = AssetCreated(
            asset_id=asset.id,
            asset_code=asset.asset_code,
            entity_id=asset.entity_id,
            tenant_id=tenant_id,
        )

        return _to_response(asset), event

    async def get_asset(
        self, asset_id: UUID, tenant_id: Optional[UUID] = None
    ) -> Optional[AssetResponse]:
        """Get asset by ID."""
        asset = await self._uow.assets.get_by_id(asset_id, tenant_id)
        if asset is None:
            return None
        return _to_response(asset)

    async def get_asset_by_code(self, asset_code: str) -> Optional[AssetResponse]:
        """Get asset by unique code."""
        asset = await self._uow.assets.get_by_code(asset_code)
        if asset is None:
            return None
        return _to_response(asset)

    async def get_asset_by_entity(self, entity_id: UUID) -> Optional[AssetResponse]:
        """Get asset bound to an entity (1:1 relationship)."""
        asset = await self._uow.assets.get_by_entity(entity_id)
        if asset is None:
            return None
        return _to_response(asset)

    async def list_assets(
        self,
        asset_class: Optional[str] = None,
        tenant_id: Optional[UUID] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> AssetListResponse:
        """List assets with optional class filter."""
        if asset_class:
            items = await self._uow.assets.list_by_class(asset_class, tenant_id, limit, offset)
        else:
            items = await self._uow.assets.list(tenant_id=tenant_id, limit=limit, offset=offset)

        return AssetListResponse(
            items=[_to_response(a) for a in items],
            total=len(items),
            limit=limit,
            offset=offset,
        )

    async def update_asset(
        self, asset_id: UUID, data: dict, tenant_id: Optional[UUID] = None
    ) -> AssetResponse:
        """Update an asset."""
        asset = await self._uow.assets.get_by_id(asset_id, tenant_id)
        if asset is None:
            raise EntityNotFound(asset_id, "Asset")

        for field_name, value in data.items():
            if value is not None and hasattr(asset, field_name):
                setattr(asset, field_name, value)

        asset = await self._uow.assets.update(asset)
        await self._uow.commit()

        return _to_response(asset)

    async def delete_asset(self, asset_id: UUID, tenant_id: Optional[UUID] = None) -> bool:
        """Soft delete an asset."""
        deleted = await self._uow.assets.soft_delete(asset_id, tenant_id)
        if deleted:
            await self._uow.commit()
        return deleted

    @property
    def events(self):
        return {
            "asset_created": AssetCreated,
            "asset_bound": AssetBound,
            "asset_unbound": AssetUnbound,
        }
