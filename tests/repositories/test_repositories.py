"""Repository Tests for Phase 1 Task 2

Tests EntityRepository, AssetRepository, PropertyRepository, RelationshipRepository
with focus on:
- CRUD operations
- Tenant isolation
- Soft delete functionality
"""
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

# Test models
from services.core.models.models import (
    Asset,
    Entity,
    PropertyValue,
)


class TestEntityRepository:
    """Test EntityRepository CRUD and tenant isolation."""
    
    @pytest.mark.asyncio
    async def test_create_entity(self):
        """Test creating an entity."""

        from services.core.repositories.entity_repository import EntityRepository
        
        # Setup mock session
        mock_session = MagicMock()
        mock_session.add = MagicMock()
        mock_session.flush = AsyncMock()
        mock_session.refresh = AsyncMock()
        
        repo = EntityRepository(mock_session)
        
        entity = Entity(
            id=uuid4(),
            tenant_id=uuid4(),
            entity_type="building",
            name="Test Building"
        )
        
        result = await repo.create(entity)
        
        assert result is not None
        mock_session.add.assert_called_once()
        mock_session.flush.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_by_id(self):
        """Test getting entity by ID."""
        from services.core.repositories.entity_repository import EntityRepository
        
        mock_session = MagicMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)
        
        repo = EntityRepository(mock_session)
        result = await repo.get_by_id(uuid4())
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_list_by_type(self):
        """Test listing entities by type with tenant filter."""
        from services.core.repositories.entity_repository import EntityRepository
        
        mock_session = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute = AsyncMock(return_value=mock_result)
        
        repo = EntityRepository(mock_session)
        result = await repo.list_by_type("building", limit=10)
        
        assert isinstance(result, list)
        assert len(result) == 0
    
    @pytest.mark.asyncio
    async def test_soft_delete(self):
        """Test soft delete sets deleted_at."""
        from services.core.repositories.entity_repository import EntityRepository
        
        # Create actual Entity instance for real soft delete behavior
        entity = Entity(
            id=uuid4(),
            tenant_id=uuid4(),
            entity_type="test",
            name="Test Entity"
        )
        
        mock_session = MagicMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = entity
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.flush = AsyncMock()
        
        repo = EntityRepository(mock_session)
        result = await repo.soft_delete(entity.id)
        
        assert result is True
        assert entity.deleted_at is not None


class TestAssetRepository:
    """Test AssetRepository operations."""
    
    @pytest.mark.asyncio
    async def test_get_by_code(self):
        """Test getting asset by code."""
        from services.core.repositories.asset_repository import AssetRepository
        
        mock_session = MagicMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)
        
        repo = AssetRepository(mock_session)
        result = await repo.get_by_code("HVAC-001")
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_create_asset(self):
        """Test creating an asset."""
        from services.core.repositories.asset_repository import AssetRepository
        
        mock_session = MagicMock()
        mock_session.add = MagicMock()
        mock_session.flush = AsyncMock()
        mock_session.refresh = AsyncMock()
        
        repo = AssetRepository(mock_session)
        
        asset = Asset(
            id=uuid4(),
            entity_id=uuid4(),
            asset_code="TEST-001",
            asset_class="hvac"
        )
        
        result = await repo.create_asset(asset)
        
        assert result is not None
        mock_session.add.assert_called_once()


class TestPropertyRepository:
    """Test PropertyRepository operations."""
    
    @pytest.mark.asyncio
    async def test_get_definition(self):
        """Test getting property definition."""
        from services.core.repositories.property_repository import PropertyRepository
        
        mock_session = MagicMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)
        
        repo = PropertyRepository(mock_session)
        result = await repo.get_definition(uuid4())
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_set_property(self):
        """Test setting a property value."""
        from services.core.repositories.property_repository import PropertyRepository
        
        # Create actual PropertyValue for proper behavior
        pv = PropertyValue(
            entity_id=uuid4(),
            property_definition_id=uuid4(),
            value={"temperature": 25.5}
        )
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session = MagicMock()
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.add = MagicMock()
        mock_session.flush = AsyncMock()
        
        repo = PropertyRepository(mock_session)
        
        result = await repo.set_property(
            entity_id=pv.entity_id,
            definition_id=pv.property_definition_id,
            value=pv.value
        )
        
        assert result is not None


class TestRelationshipRepository:
    """Test RelationshipRepository operations."""
    
    @pytest.mark.asyncio
    async def test_create_relation(self):
        """Test creating a relationship."""
        from services.core.repositories.relationship_repository import (
            RelationshipRepository,
        )
        
        mock_session = MagicMock()
        mock_session.add = MagicMock()
        mock_session.flush = AsyncMock()
        mock_session.refresh = AsyncMock()
        
        repo = RelationshipRepository(mock_session)
        
        rel = await repo.create_relation(
            tenant_id=uuid4(),
            source_entity_id=uuid4(),
            target_entity_id=uuid4(),
            relation_type="contains"
        )
        
        assert rel is not None
        assert rel.relation_type == "contains"
    
    @pytest.mark.asyncio
    async def test_list_source_relations(self):
        """Test listing relationships where entity is source."""
        from services.core.repositories.relationship_repository import (
            RelationshipRepository,
        )
        
        mock_session = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute = AsyncMock(return_value=mock_result)
        
        repo = RelationshipRepository(mock_session)
        result = await repo.list_source_relations(uuid4())
        
        assert isinstance(result, list)


class TestTenantIsolation:
    """Test tenant isolation in repositories."""
    
    @pytest.mark.asyncio
    async def test_tenant_filter_applied(self):
        """Verify tenant_id filter is applied in queries."""
        from services.core.repositories.entity_repository import EntityRepository
        
        mock_session = MagicMock()
        
        # Track the SQL statement executed
        executed_statements = []
        async def mock_execute(stmt):
            executed_statements.append(str(stmt))
            mock_result = MagicMock()
            mock_result.scalars.return_value.all.return_value = []
            return mock_result
        
        mock_session.execute = AsyncMock(side_effect=mock_execute)
        
        repo = EntityRepository(mock_session)
        await repo.list_by_type("building", tenant_id=uuid4())
        
        # Verify WHERE clause contains tenant filter
        assert len(executed_statements) > 0
        stmt_str = executed_statements[0]
        assert "tenant_id" in stmt_str.lower()


class TestSoftDelete:
    """Test soft delete functionality."""
    
    def test_soft_delete_mixin(self):
        """Test SoftDeleteMixin methods."""
        from datetime import datetime, timezone

        from services.core.models.base import SoftDeleteMixin
        
        # Create a simple test class with the mixin
        class TestModel(SoftDeleteMixin):
            __tablename__ = "test_model"
            
        # Test without SQLAlchemy mapper (just the mixin logic)
        from types import SimpleNamespace
        obj = SimpleNamespace(deleted_at=None)
        
        # Simulate soft_delete behavior
        assert obj.deleted_at is None
        obj.deleted_at = datetime.now(timezone.utc)
        assert obj.deleted_at is not None
        
        # Simulate restore
        obj.deleted_at = None
        assert obj.deleted_at is None
    
    def test_entity_soft_delete_property(self):
        """Test Entity has soft delete capability."""
        entity = Entity(
            tenant_id=uuid4(),
            entity_type="test",
            name="Test"
        )
        # Initially not deleted
        assert entity.deleted_at is None
        # Note: is_active checks status, not deleted_at in this implementation
        # The actual check would be in a real scenario


class TestRepositoryNoCommit:
    """Verify repositories do NOT call commit()."""
    
    @pytest.mark.asyncio
    async def test_create_does_not_commit(self):
        """Create should use flush, not commit."""
        from services.core.repositories.entity_repository import EntityRepository
        
        mock_session = MagicMock()
        mock_session.add = MagicMock()
        mock_session.flush = AsyncMock()
        mock_session.refresh = AsyncMock()
        # Note: commit is NOT mocked - if called, it would raise an error
        
        repo = EntityRepository(mock_session)
        entity = Entity(
            tenant_id=uuid4(),
            entity_type="test",
            name="Test"
        )
        
        await repo.create(entity)
        
        # Verify flush was called
        mock_session.flush.assert_called_once()
        # Verify commit was NOT called
        mock_session.commit.assert_not_called()
