"""PropertyService Tests for Phase 1 Task 3"""
import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock, AsyncMock
from uuid import uuid4

from services.core.models.models import PropertyDefinition, PropertyValue, Entity
from services.core.services.property_service import PropertyService
from services.core.schemas.property import PropertyDefinitionCreate, PropertyValueResponse
from services.core.unit_of_work import UnitOfWork
from services.exceptions.base import InvalidPropertyType
from services.exceptions.entity import ValidationError


class TestPropertyService:
    """Test PropertyService operations."""

    def _make_mock_defn(self, **kwargs) -> PropertyDefinition:
        """Create a mock property definition."""
        now = datetime.now(timezone.utc)
        defn = MagicMock()
        defn.id = kwargs.get("id", uuid4())
        defn.tenant_id = kwargs.get("tenant_id", uuid4())
        defn.entity_type = kwargs.get("entity_type", "building")
        defn.key = kwargs.get("key", "temperature")
        defn.data_type = kwargs.get("data_type", "FLOAT")
        defn.unit = kwargs.get("unit", "celsius")
        defn.required = kwargs.get("required", False)
        defn.writable = kwargs.get("writable", True)
        defn.extra_data = kwargs.get("extra_data", {})
        defn.created_at = kwargs.get("created_at", now)
        defn.updated_at = kwargs.get("updated_at", now)
        defn.deleted_at = None
        return defn

    def _make_mock_pv(self, **kwargs) -> PropertyValue:
        """Create a mock property value."""
        now = datetime.now(timezone.utc)
        pv = MagicMock()
        pv.entity_id = kwargs.get("entity_id", uuid4())
        pv.property_definition_id = kwargs.get("definition_id", uuid4())
        pv.value = kwargs.get("value", {"value": 25.5})
        pv.updated_at = kwargs.get("updated_at", now)
        return pv

    @pytest.mark.asyncio
    async def test_define_property_success(self):
        """Test creating a property definition."""
        uow = MagicMock(spec=UnitOfWork)
        uow.properties = MagicMock()
        uow.commit = AsyncMock()

        mock_defn = self._make_mock_defn(data_type="FLOAT")
        uow.properties.get_definition_by_key = AsyncMock(return_value=None)
        uow.properties.create_definition = AsyncMock(return_value=mock_defn)

        service = PropertyService(uow)

        data = PropertyDefinitionCreate(
            entity_type="building",
            key="temperature",
            data_type="FLOAT",
            unit="celsius",
            required=False,
            writable=True,
            metadata={}
        )

        result, event = await service.define_property(data, uuid4())

        assert result is not None
        assert result.key == "temperature"
        assert result.data_type == "FLOAT"
        uow.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_define_property_invalid_type(self):
        """Test creating property with invalid type should fail."""
        from pydantic import ValidationError
        
        # Pydantic validates data_type at schema level - INVALID_TYPE fails here
        with pytest.raises(ValidationError):
            data = PropertyDefinitionCreate(
                entity_type="building",
                key="temperature",
                data_type="INVALID_TYPE",
            )

    @pytest.mark.asyncio
    async def test_set_property_type_validation_pass(self):
        """Test setting property value with correct type."""
        uow = MagicMock(spec=UnitOfWork)
        uow.properties = MagicMock()
        uow.entities = MagicMock()
        uow.commit = AsyncMock()

        mock_defn = self._make_mock_defn(data_type="FLOAT")
        uow.properties.get_definition = AsyncMock(return_value=mock_defn)

        mock_entity = MagicMock()
        mock_entity.id = uuid4()
        uow.entities.get_by_id = AsyncMock(return_value=mock_entity)

        mock_pv = self._make_mock_pv(value={"value": 25.5})
        uow.properties.set_property = AsyncMock(return_value=mock_pv)

        service = PropertyService(uow)

        result, event = await service.set_property(
            entity_id=mock_entity.id,
            definition_id=mock_defn.id,
            value=25.5
        )

        assert result is not None
        assert result.value == {"value": 25.5}

    @pytest.mark.asyncio
    async def test_set_property_type_validation_fail(self):
        """Test setting property value with wrong type should fail."""
        uow = MagicMock(spec=UnitOfWork)
        uow.properties = MagicMock()
        uow.entities = MagicMock()
        uow.commit = AsyncMock()

        mock_defn = self._make_mock_defn(data_type="FLOAT")
        uow.properties.get_definition = AsyncMock(return_value=mock_defn)

        mock_entity = MagicMock()
        mock_entity.id = uuid4()
        uow.entities.get_by_id = AsyncMock(return_value=mock_entity)

        service = PropertyService(uow)

        # Try to set string value to FLOAT property - should fail
        with pytest.raises(InvalidPropertyType):
            await service.set_property(
                entity_id=mock_entity.id,
                definition_id=mock_defn.id,
                value="abc"  # String instead of float
            )

    @pytest.mark.asyncio
    async def test_set_property_boolean_coercion(self):
        """Test boolean type coercion from string."""
        uow = MagicMock(spec=UnitOfWork)
        uow.properties = MagicMock()
        uow.entities = MagicMock()
        uow.commit = AsyncMock()

        mock_defn = self._make_mock_defn(data_type="BOOLEAN")
        uow.properties.get_definition = AsyncMock(return_value=mock_defn)

        mock_entity = MagicMock()
        mock_entity.id = uuid4()
        uow.entities.get_by_id = AsyncMock(return_value=mock_entity)

        mock_pv = self._make_mock_pv(value={"value": True})
        uow.properties.set_property = AsyncMock(return_value=mock_pv)

        service = PropertyService(uow)

        result, event = await service.set_property(
            entity_id=mock_entity.id,
            definition_id=mock_defn.id,
            value="true"  # String should be coerced to bool
        )

        assert result is not None

    @pytest.mark.asyncio
    async def test_get_properties_for_entity(self):
        """Test getting all properties for an entity."""
        uow = MagicMock(spec=UnitOfWork)
        uow.properties = MagicMock()

        mock_pvs = [
            self._make_mock_pv(entity_id=uuid4(), value={"value": 25.5}),
            self._make_mock_pv(entity_id=uuid4(), value={"value": True}),
        ]
        uow.properties.get_properties = AsyncMock(return_value=mock_pvs)

        service = PropertyService(uow)
        results = await service.get_properties(mock_pvs[0].entity_id)

        assert len(results) == 2
