"""Test TwinEntityRegistry — In-memory runtime registry."""
import pytest
from uuid import uuid4

from services.twin.models import TwinEntity
from services.twin.registry import TwinEntityRegistry
from services.twin.exceptions import TwinEntityAlreadyExistsError


class TestTwinEntityRegistry:
    """Tests for TwinEntityRegistry."""

    def setup_method(self):
        """Setup fresh registry for each test."""
        self.registry = TwinEntityRegistry()
        self.tenant_id = uuid4()

    def test_register_and_get_entity(self):
        """Test basic register and get operations."""
        entity = TwinEntity(
            tenant_id=self.tenant_id,
            name="Test Pump",
            entity_type="pump",
        )
        registered = self.registry.register(entity)

        assert registered.id is not None
        assert registered.name == "Test Pump"
        assert registered.entity_type == "pump"

        retrieved = self.registry.get(registered.id, self.tenant_id)
        assert retrieved is not None
        assert retrieved.id == registered.id

    def test_register_duplicate_raises_error(self):
        """Test that registering duplicate entity raises error."""
        entity = TwinEntity(
            tenant_id=self.tenant_id,
            name="Test Entity",
        )
        self.registry.register(entity)

        # Try to register same entity again
        with pytest.raises(TwinEntityAlreadyExistsError):
            self.registry.register(entity)

    def test_remove_entity(self):
        """Test removing an entity."""
        entity = TwinEntity(tenant_id=self.tenant_id, name="ToRemove")
        registered = self.registry.register(entity)

        removed = self.registry.remove(registered.id, self.tenant_id)
        assert removed is True

        # Verify it's gone
        retrieved = self.registry.get(registered.id, self.tenant_id)
        assert retrieved is None

    def test_remove_nonexistent_entity(self):
        """Test removing non-existent entity returns False."""
        fake_id = uuid4()
        removed = self.registry.remove(fake_id, self.tenant_id)
        assert removed is False

    def test_list_entities_with_pagination(self):
        """Test listing entities with pagination."""
        # Create multiple entities
        for i in range(5):
            entity = TwinEntity(
                tenant_id=self.tenant_id,
                name=f"Entity {i}",
                entity_type="sensor",
            )
            self.registry.register(entity)

        # List all
        all_entities = self.registry.list(self.tenant_id, limit=100)
        assert len(all_entities) == 5

        # Paginate
        page1 = self.registry.list(self.tenant_id, limit=2, offset=0)
        page2 = self.registry.list(self.tenant_id, limit=2, offset=2)

        assert len(page1) == 2
        assert len(page2) == 2
        assert page1[0].name != page2[0].name

    def test_count_entities(self):
        """Test counting entities per tenant."""
        # Add entities
        for i in range(3):
            entity = TwinEntity(tenant_id=self.tenant_id, name=f"Entity {i}")
            self.registry.register(entity)

        count = self.registry.count(self.tenant_id)
        assert count == 3

    def test_tenant_isolation(self):
        """Test that entities are isolated by tenant."""
        tenant_a = uuid4()
        tenant_b = uuid4()

        # Register entity for tenant A
        entity_a = TwinEntity(tenant_id=tenant_a, name="TenantA Entity")
        self.registry.register(entity_a)

        # Register entity for tenant B
        entity_b = TwinEntity(tenant_id=tenant_b, name="TenantB Entity")
        self.registry.register(entity_b)

        # Verify isolation
        result_a = self.registry.get(entity_a.id, tenant_a)
        result_b = self.registry.get(entity_b.id, tenant_b)

        assert result_a is not None
        assert result_b is not None
        assert result_a.id != result_b.id

        # Cross-tenant access should return None
        wrong_access = self.registry.get(entity_a.id, tenant_b)
        assert wrong_access is None

    def test_contains_check(self):
        """Test contains method."""
        entity = TwinEntity(tenant_id=self.tenant_id, name="Contains Test")
        self.registry.register(entity)

        assert self.registry.contains(entity.id, self.tenant_id) is True
        assert self.registry.contains(uuid4(), self.tenant_id) is False

    def test_clear_all_entities(self):
        """Test clearing all entities for a tenant."""
        for i in range(3):
            entity = TwinEntity(tenant_id=self.tenant_id, name=f"Clear {i}")
            self.registry.register(entity)

        cleared = self.registry.clear(self.tenant_id)
        assert cleared == 3
        assert self.registry.count(self.tenant_id) == 0
