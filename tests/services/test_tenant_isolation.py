"""Tenant Isolation Tests for Phase 1 Task 3"""
import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock, AsyncMock
from uuid import uuid4

from services.core.services.entity_service import EntityService
from services.core.services.asset_service import AssetService
from services.core.schemas.asset import AssetCreate
from services.core.unit_of_work import UnitOfWork


class TestTenantIsolation:
    """Test tenant isolation across services."""

    def _make_mock_entity(self, **kwargs):
        """Create a mock entity."""
        now = datetime.now(timezone.utc)
        entity = MagicMock()
        entity.id = kwargs.get("id", uuid4())
        entity.tenant_id = kwargs.get("tenant_id", uuid4())
        entity.entity_type = kwargs.get("entity_type", "building")
        entity.name = kwargs.get("name", "Test")
        entity.description = kwargs.get("description")
        entity.status = kwargs.get("status", "active")
        entity.extra_data = kwargs.get("extra_data", {})
        entity.created_at = kwargs.get("created_at", now)
        entity.updated_at = kwargs.get("updated_at", now)
        return entity

    @pytest.mark.asyncio
    async def test_entity_tenant_filter(self):
        """Entities should be filtered by tenant."""
        uow = MagicMock(spec=UnitOfWork)
        uow.entities = MagicMock()
        uow.commit = AsyncMock()

        tenant_a = uuid4()
        tenant_b = uuid4()

        mock_entity_a = self._make_mock_entity(tenant_id=tenant_a, name="Building A")

        # When queried with tenant_a, should only return entity_a's data
        uow.entities.get_by_id = AsyncMock(return_value=mock_entity_a)

        service = EntityService(uow)

        # Should find entity when querying with correct tenant
        result = await service.get_entity(mock_entity_a.id, tenant_a)
        assert result is not None

        # Same query with different tenant should not find the entity
        uow.entities.get_by_id = AsyncMock(return_value=None)
        result = await service.get_entity(mock_entity_a.id, tenant_b)
        assert result is None

    @pytest.mark.asyncio
    async def test_asset_entity_binding_respects_tenant(self):
        """Asset creation should validate entity belongs to same tenant."""
        uow = MagicMock(spec=UnitOfWork)
        uow.entities = MagicMock()
        assets_mock = MagicMock()
        assets_mock.create_asset = AsyncMock()
        assets_mock.get_by_code = AsyncMock(return_value=None)
        uow.assets = assets_mock
        uow.commit = AsyncMock()

        tenant_a = uuid4()
        tenant_b = uuid4()

        # Entity from tenant_a
        entity_a = self._make_mock_entity(tenant_id=tenant_a, name="Building A")
        entity_a.id = uuid4()
        # Set created_at on mock entity for _to_response
        entity_a.created_at = datetime.now(timezone.utc)
        entity_a.updated_at = datetime.now(timezone.utc)
        entity_a.deleted_at = None

        # Mock the asset return value
        mock_asset = MagicMock()
        mock_asset.id = uuid4()
        mock_asset.entity_id = entity_a.id
        mock_asset.asset_code = "HVAC-001"
        mock_asset.asset_class = "hvac"
        mock_asset.lifecycle_status = "active"
        mock_asset.manufacturer = None
        mock_asset.model = None
        mock_asset.serial_number = None
        mock_asset.installed_at = None
        mock_asset.extra_data = {}
        mock_asset.created_at = datetime.now(timezone.utc)
        mock_asset.updated_at = datetime.now(timezone.utc)
        mock_asset.deleted_at = None
        assets_mock.create_asset = AsyncMock(return_value=mock_asset)

        # When we query for entity_a with tenant_a, we get it
        uow.entities.get_by_id = AsyncMock(return_value=entity_a)

        service = AssetService(uow)

        # Should succeed - entity belongs to same tenant
        data = AssetCreate(
            entity_id=entity_a.id,
            asset_code="HVAC-001",
            asset_class="hvac",
        )
        result, _ = await service.create_asset(data, tenant_a)
        assert result is not None
        assert result.asset_code == "HVAC-001"

        # When we query for entity_a with tenant_b, should not find it
        uow.entities.get_by_id = AsyncMock(return_value=None)

        # Should fail - entity doesn't belong to this tenant
        from services.exceptions.base import EntityNotFound
        with pytest.raises(EntityNotFound):
            await service.create_asset(data, tenant_b)

    @pytest.mark.asyncio
    async def test_list_entities_uses_tenant_context(self):
        """List entities should use tenant context from UnitOfWork."""
        uow = MagicMock(spec=UnitOfWork)
        uow.entities = MagicMock()
        uow.commit = AsyncMock()

        tenant_id = uuid4()

        mock_entities = [
            self._make_mock_entity(tenant_id=tenant_id, name="Building 1"),
            self._make_mock_entity(tenant_id=tenant_id, name="Building 2"),
        ]
        uow.entities.list = AsyncMock(return_value=mock_entities)

        service = EntityService(uow)
        await service.list_entities(tenant_id=tenant_id)

        # Verify list was called with tenant filter
        uow.entities.list.assert_called_once()
        call_args = uow.entities.list.call_args
        assert call_args[1].get("tenant_id") == tenant_id or \
               (len(call_args[0]) > 1 and call_args[0][1] == tenant_id)
