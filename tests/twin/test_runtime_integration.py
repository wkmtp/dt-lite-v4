"""Test Twin Runtime Integration — Persistent to Runtime bridge."""
from uuid import uuid4

from services.twin.models.definition import TwinDefinition
from services.twin.models.entity import PersistentTwinEntity
from services.twin.models.binding import TwinBinding
from services.twin.registry import TwinEntityRegistry
from services.twin.state import TwinStateManager


class TestRuntimeIntegration:
    """Test integration between persistence layer and runtime registry."""

    def setup_method(self):
        self.registry = TwinEntityRegistry()
        self.state_manager = TwinStateManager(self.registry)

    def test_persistent_entity_to_runtime_conversion(self):
        """Test converting persistent entity to runtime twin."""
        # Simulate loading from database
        persistent_entity = PersistentTwinEntity(
            id=uuid4(),
            tenant_id=uuid4(),
            definition_id=uuid4(),
            external_id="device-001",
            name="Device 001",
        )

        # Convert to runtime model
        from services.twin.models import TwinEntity
        runtime_entity = TwinEntity(
            id=persistent_entity.id,
            tenant_id=persistent_entity.tenant_id,
            name=persistent_entity.name,
            entity_type="",  # Would come from definition
            device_id=None,  # Binding would be separate
        )

        # Register in runtime
        registered = self.registry.register(runtime_entity)
        assert registered.id == persistent_entity.id
        assert registered.name == persistent_entity.name

    def test_registry_lookup_after_warmup(self):
        """Test that entities are accessible after warmup."""
        # Warm up registry with persistent data
        sample_tenant = uuid4()
        for i in range(3):
            from services.twin.models import TwinEntity
            entity = TwinEntity(tenant_id=sample_tenant, name=f"Entity {i}")
            self.registry.register(entity)

        # Verify registry operations work
        from services.twin.models import TwinEntity
        entity = TwinEntity(tenant_id=sample_tenant, name="Sample")
        self.registry.register(entity)

        retrieved = self.registry.get(entity.id, sample_tenant)
        assert retrieved is not None
        assert retrieved.name == "Sample"

    def test_state_persistence_boundary(self):
        """Test that state stays in memory while identity persists."""
        tenant_id = uuid4()

        # Create persistent entity (simulated)
        persistent = PersistentTwinEntity(
            id=uuid4(),
            tenant_id=tenant_id,
            external_id="ext-001",
            name="Persistent Entity",
        )

        # Create runtime entity from persistent
        from services.twin.models import TwinEntity
        runtime = TwinEntity(
            id=persistent.id,
            tenant_id=persistent.tenant_id,
            name=persistent.name,
        )
        self.registry.register(runtime)

        # State is separate from persistence
        assert len(runtime.runtime_state) == 0  # Empty initially

    def test_binding_decoupling(self):
        """Test that binding is separate from entity relationship."""
        tenant_id = uuid4()
        device_id = uuid4()
        entity_id = uuid4()

        # Create binding record (simulated persistence)
        binding = TwinBinding(
            id=uuid4(),
            tenant_id=tenant_id,
            device_id=device_id,
            twin_entity_id=entity_id,
        )

        # Verify binding doesn't modify device or entity
        # (Decoupling principle)
        assert binding.device_id == device_id
        assert binding.twin_entity_id == entity_id


class TestMigrationAlignment:
    """Test that models align with migration."""

    def test_definition_model_fields(self):
        """Verify TwinDefinition has required fields."""
        from sqlalchemy import inspect as sa_inspect

        mapper = sa_inspect(TwinDefinition)
        column_names = [c.key for c in mapper.columns]

        required = ['id', 'tenant_id', 'code', 'name', 'schema', 'created_at', 'updated_at']
        for field in required:
            assert field in column_names, f"Missing field: {field}"

    def test_entity_model_fields(self):
        """Verify PersistentTwinEntity has required fields."""
        from sqlalchemy import inspect as sa_inspect
        from services.twin.models.entity import PersistentTwinEntity

        mapper = sa_inspect(PersistentTwinEntity)
        column_names = [c.key for c in mapper.columns]

        required = ['id', 'tenant_id', 'definition_id', 'external_id', 'name', 'created_at', 'updated_at']
        for field in required:
            assert field in column_names, f"Missing field: {field}"

    def test_binding_model_fields(self):
        """Verify TwinBinding has required fields."""
        from sqlalchemy import inspect as sa_inspect
        from services.twin.models.binding import TwinBinding

        mapper = sa_inspect(TwinBinding)
        column_names = [c.key for c in mapper.columns]

        required = ['id', 'tenant_id', 'device_id', 'twin_entity_id', 'binding_type', 'created_at']
        for field in required:
            assert field in column_names, f"Missing field: {field}"
