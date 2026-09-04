"""Phase 1 Tests for Core Service - Entity, Asset, Property, Relationship"""
import pytest
from unittest.mock import MagicMock, AsyncMock
from datetime import datetime, timezone
import uuid

from services.core.models.models import Entity, Asset, PropertyDefinition, PropertyValue, Relationship


class TestEntityModel:
    def test_entity_creation(self):
        """Test creating an entity instance"""
        entity = Entity(
            id=uuid.uuid4(),
            tenant_id=uuid.uuid4(),
            entity_type="building",
            name="Test Building",
            status="active"
        )
        assert entity.name == "Test Building"
        assert entity.entity_type == "building"
        assert entity.status == "active"
    
    def test_entity_is_active_property(self):
        """Test is_active property"""
        entity = Entity(status="active")
        assert entity.is_active is True
        
        entity.status = "inactive"
        assert entity.is_active is False


class TestAssetModel:
    def test_asset_creation(self):
        """Test creating an asset instance"""
        asset = Asset(
            id=uuid.uuid4(),
            entity_id=uuid.uuid4(),
            asset_code="HVAC-001",
            asset_class="hvac",
            lifecycle_status="active"
        )
        assert asset.asset_code == "HVAC-001"
        assert asset.lifecycle_status == "active"
    
    def test_asset_is_active_property(self):
        """Test is_active property"""
        asset = Asset(lifecycle_status="active")
        assert asset.is_active is True
        
        asset.lifecycle_status = "retired"
        assert asset.is_active is False


class TestPropertyModels:
    def test_property_definition_creation(self):
        """Test creating a property definition"""
        prop_def = PropertyDefinition(
            id=uuid.uuid4(),
            entity_type="hvac",
            key="temperature",
            data_type="number"
        )
        assert prop_def.key == "temperature"
        assert prop_def.data_type == "number"
    
    def test_property_value_creation(self):
        """Test creating a property value"""
        prop_value = PropertyValue(
            entity_id=uuid.uuid4(),
            property_definition_id=uuid.uuid4(),
            value={"temperature": 25.5}
        )
        assert prop_value.value == {"temperature": 25.5}


class TestRelationshipModel:
    def test_relationship_creation(self):
        """Test creating a relationship"""
        rel = Relationship(
            id=uuid.uuid4(),
            tenant_id=uuid.uuid4(),
            source_entity_id=uuid.uuid4(),
            target_entity_id=uuid.uuid4(),
            relation_type="contains"
        )
        assert rel.relation_type == "contains"
        assert rel.source_entity_id != rel.target_entity_id


class TestEntityService:
    @pytest.mark.asyncio
    async def test_list_entities_empty(self):
        """Test listing entities returns empty when no data"""
        db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        db.execute = AsyncMock(return_value=mock_result)
        
        from services.core.services.core_service import EntityService
        service = EntityService(db)
        entities = await service.list_entities(str(uuid.uuid4()), None, 0, 20)
        
        assert isinstance(entities, list)
        assert len(entities) == 0


class TestRelationshipService:
    @pytest.mark.asyncio
    async def test_list_relationships_empty(self):
        """Test listing relationships returns empty when no data"""
        db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        db.execute = AsyncMock(return_value=mock_result)
        
        from services.core.services.core_service import RelationshipService
        service = RelationshipService(db)
        relationships = await service.list_relationships(str(uuid.uuid4()), None)
        
        assert isinstance(relationships, list)


class TestPropertyService:
    @pytest.mark.asyncio
    async def test_create_property_definition(self):
        """Test property definition creation with mock"""
        db = AsyncMock()
        db.commit = AsyncMock()
        
        from services.core.services.core_service import PropertyService
        service = PropertyService(db)
        
        # Mock add and refresh
        mock_prop_def = MagicMock()
        mock_prop_def.id = uuid.uuid4()
        db.add = MagicMock()
        
        data = {
            "tenant_id": str(uuid.uuid4()),
            "entity_type": "hvac",
            "key": "temperature",
            "data_type": "number",
            "unit": "celsius"
        }
        
        result = await service.create_property_definition(data)
        db.add.assert_called_once()


class TestAssetService:
    @pytest.mark.asyncio
    async def test_get_asset_by_code(self):
        """Test getting asset by code"""
        db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        db.execute = AsyncMock(return_value=mock_result)
        
        from services.core.services.core_service import AssetService
        service = AssetService(db)
        asset = await service.get_asset_by_code("HVAC-001")
        
        assert asset is None
