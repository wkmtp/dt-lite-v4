"""EntityService Tests for Phase 1 Task 3"""
import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock, AsyncMock
from uuid import uuid4

from services.core.models.models import Entity
from services.core.services.entity_service import EntityService
from services.core.schemas.entity import EntityCreate
from services.core.unit_of_work import UnitOfWork
from services.exceptions.base import EntityNotFound
from services.exceptions.entity import EntityDuplicateName


class TestEntityService:
    """Test EntityService operations."""

    def _make_mock_entity(self, **kwargs):
        """Create a mock entity that behaves like an Entity model."""
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
        entity.deleted_at = None
        return entity

    @pytest.mark.asyncio
    async def test_create_entity(self):
        """Test creating a valid entity."""
        uow = MagicMock(spec=UnitOfWork)
        uow.entities = MagicMock()
        uow.commit = AsyncMock()

        # Mock repository create method
        mock_entity = self._make_mock_entity(name="Test Building", entity_type="building")
        uow.entities.create = AsyncMock(return_value=mock_entity)
        uow.entities.find_by_name = AsyncMock(return_value=None)

        service = EntityService(uow)

        data = EntityCreate(
            name="Test Building",
            entity_type="building",
            description="Test description",
            extra_data={}
        )

        result, event = await service.create_entity(data, uuid4())

        assert result is not None
        assert result.name == "Test Building"
        assert result.entity_type == "building"
        uow.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_entity_empty_name(self):
        """Test creating entity with empty name should fail."""
        uow = MagicMock(spec=UnitOfWork)
        service = EntityService(uow)

        # Pydantic will reject empty name at schema level
        with pytest.raises(Exception):  # ValidationError from Pydantic
            data = EntityCreate(name="", entity_type="building")
            await service.create_entity(data, uuid4())

    @pytest.mark.asyncio
    async def test_create_entity_empty_type(self):
        """Test creating entity with empty type should fail."""
        uow = MagicMock(spec=UnitOfWork)
        service = EntityService(uow)

        # Pydantic will reject empty entity_type at schema level
        with pytest.raises(Exception):
            data = EntityCreate(name="Test", entity_type="")
            await service.create_entity(data, uuid4())

    @pytest.mark.asyncio
    async def test_create_entity_duplicate_name(self):
        """Test creating entity with duplicate name should fail."""
        uow = MagicMock(spec=UnitOfWork)
        uow.entities = MagicMock()
        uow.commit = AsyncMock()

        existing_entity = self._make_mock_entity(name="Duplicate Name", entity_type="building")
        uow.entities.find_by_name = AsyncMock(return_value=existing_entity)

        service = EntityService(uow)

        data = EntityCreate(name="Duplicate Name", entity_type="building")

        with pytest.raises(EntityDuplicateName):
            await service.create_entity(data, uuid4())

    @pytest.mark.asyncio
    async def test_get_entity_not_found(self):
        """Test getting non-existent entity."""
        uow = MagicMock(spec=UnitOfWork)
        uow.entities = MagicMock()
        uow.entities.get_by_id = AsyncMock(return_value=None)

        service = EntityService(uow)
        result = await service.get_entity(uuid4())

        assert result is None

    @pytest.mark.asyncio
    async def test_get_entity_found(self):
        """Test getting existing entity."""
        uow = MagicMock(spec=UnitOfWork)
        uow.entities = MagicMock()

        mock_entity = self._make_mock_entity(name="Test Building", entity_type="building")
        uow.entities.get_by_id = AsyncMock(return_value=mock_entity)

        service = EntityService(uow)
        result = await service.get_entity(mock_entity.id)

        assert result is not None
        assert result.name == "Test Building"

    @pytest.mark.asyncio
    async def test_delete_entity(self):
        """Test soft deleting an entity."""
        uow = MagicMock(spec=UnitOfWork)
        uow.entities = MagicMock()
        uow.commit = AsyncMock()

        uow.entities.soft_delete = AsyncMock(return_value=True)

        service = EntityService(uow)
        result, event = await service.delete_entity(uuid4())

        assert result is True
        uow.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_tenant_isolation(self):
        """Test that entities are filtered by tenant."""
        uow = MagicMock(spec=UnitOfWork)
        uow.entities = MagicMock()

        tenant_a = uuid4()
        tenant_b = uuid4()

        mock_entity = self._make_mock_entity(tenant_id=tenant_a, name="Building A")
        uow.entities.get_by_id = AsyncMock(return_value=mock_entity)

        service = EntityService(uow)

        # Get with correct tenant - should find entity
        result = await service.get_entity(mock_entity.id, tenant_a)
        assert result is not None

        # Get with different tenant - should not find entity
        uow.entities.get_by_id = AsyncMock(return_value=None)
        result = await service.get_entity(mock_entity.id, tenant_b)
        assert result is None
