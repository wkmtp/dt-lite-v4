"""AssetService Tests for Phase 1 Task 3"""
import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock, AsyncMock
from uuid import uuid4

from services.core.models.models import Entity
from services.core.services.asset_service import AssetService
from services.core.schemas.asset import AssetCreate
from services.core.unit_of_work import UnitOfWork
from services.exceptions.base import EntityNotFound, AssetAlreadyExists


class TestAssetService:
    """Test AssetService operations."""

    def _make_mock_asset(self, **kwargs):
        """Create a mock asset that behaves like an Asset model."""
        now = datetime.now(timezone.utc)
        asset = MagicMock()
        asset.id = kwargs.get("id", uuid4())
        asset.entity_id = kwargs.get("entity_id", uuid4())
        asset.asset_code = kwargs.get("asset_code", "TEST-001")
        asset.asset_class = kwargs.get("asset_class", "hvac")
        asset.lifecycle_status = kwargs.get("lifecycle_status", "active")
        asset.manufacturer = kwargs.get("manufacturer")
        asset.model = kwargs.get("model")
        asset.serial_number = kwargs.get("serial_number")
        asset.installed_at = kwargs.get("installed_at")
        asset.extra_data = kwargs.get("extra_data", {})
        asset.created_at = kwargs.get("created_at", now)
        asset.updated_at = kwargs.get("updated_at", now)
        asset.deleted_at = None
        return asset

    @pytest.mark.asyncio
    async def test_create_asset_success(self):
        """Test creating an asset bound to an entity."""
        uow = MagicMock(spec=UnitOfWork)
        uow.entities = MagicMock()
        uow.assets = MagicMock()
        uow.commit = AsyncMock()

        # Mock entity exists
        mock_entity = MagicMock()
        mock_entity.id = uuid4()
        mock_entity.tenant_id = uuid4()
        uow.entities.get_by_id = AsyncMock(return_value=mock_entity)

        # Mock asset creation
        mock_asset = self._make_mock_asset(entity_id=mock_entity.id, asset_code="HVAC-001")
        uow.assets.get_by_code = AsyncMock(return_value=None)
        uow.assets.create_asset = AsyncMock(return_value=mock_asset)

        service = AssetService(uow)

        data = AssetCreate(
            entity_id=mock_entity.id,
            asset_code="HVAC-001",
            asset_class="hvac",
            manufacturer="Test Manufacturer",
            extra_data={}
        )

        result, event = await service.create_asset(data, mock_entity.tenant_id)

        assert result is not None
        assert result.asset_code == "HVAC-001"
        uow.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_asset_entity_not_found(self):
        """Test creating asset with non-existent entity should fail."""
        uow = MagicMock(spec=UnitOfWork)
        uow.entities = MagicMock()
        uow.commit = AsyncMock()

        uow.entities.get_by_id = AsyncMock(return_value=None)

        service = AssetService(uow)

        data = AssetCreate(
            entity_id=uuid4(),
            asset_code="TEST-001",
            asset_class="hvac",
        )

        with pytest.raises(EntityNotFound):
            await service.create_asset(data, uuid4())

    @pytest.mark.asyncio
    async def test_create_asset_duplicate_code(self):
        """Test creating asset with duplicate code should fail."""
        uow = MagicMock(spec=UnitOfWork)
        uow.entities = MagicMock()
        uow.assets = MagicMock()
        uow.commit = AsyncMock()

        mock_entity = MagicMock()
        mock_entity.id = uuid4()
        mock_entity.tenant_id = uuid4()
        uow.entities.get_by_id = AsyncMock(return_value=mock_entity)

        existing_asset = self._make_mock_asset(asset_code="HVAC-001")
        uow.assets.get_by_code = AsyncMock(return_value=existing_asset)

        service = AssetService(uow)

        data = AssetCreate(entity_id=mock_entity.id, asset_code="HVAC-001", asset_class="hvac")

        with pytest.raises(AssetAlreadyExists):
            await service.create_asset(data, mock_entity.tenant_id)

    @pytest.mark.asyncio
    async def test_get_asset_by_code(self):
        """Test getting asset by unique code."""
        uow = MagicMock(spec=UnitOfWork)
        uow.assets = MagicMock()

        mock_asset = self._make_mock_asset(asset_code="HVAC-001")
        uow.assets.get_by_code = AsyncMock(return_value=mock_asset)

        service = AssetService(uow)
        result = await service.get_asset_by_code("HVAC-001")

        assert result is not None
        assert result.asset_code == "HVAC-001"

    @pytest.mark.asyncio
    async def test_get_asset_not_found(self):
        """Test getting non-existent asset."""
        uow = MagicMock(spec=UnitOfWork)
        uow.assets = MagicMock()
        uow.assets.get_by_id = AsyncMock(return_value=None)

        service = AssetService(uow)
        result = await service.get_asset(uuid4())

        assert result is None

    @pytest.mark.asyncio
    async def test_delete_asset(self):
        """Test soft deleting an asset."""
        uow = MagicMock(spec=UnitOfWork)
        uow.assets = MagicMock()
        uow.commit = AsyncMock()

        uow.assets.soft_delete = AsyncMock(return_value=True)

        service = AssetService(uow)
        result = await service.delete_asset(uuid4())

        assert result is True
        uow.commit.assert_called_once()
