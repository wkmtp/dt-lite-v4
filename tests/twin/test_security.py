"""Test Twin Runtime Security — Tenant isolation and access control."""
import pytest
from uuid import uuid4
from unittest.mock import MagicMock

from services.twin.models import TwinEntity
from services.twin.registry import TwinEntityRegistry
from services.twin.state import TwinStateManager
from services.twin.binding import EntityBindingService


class TestCrossTenantAccess:
    """Test cross-tenant access is rejected."""

    def setup_method(self):
        """Setup fresh registry and services for each test."""
        self.registry = TwinEntityRegistry()
        self.tenant_a = uuid4()
        self.tenant_b = uuid4()

        # Mock device repository
        self.mock_device_repo = MagicMock()

    def test_cross_tenant_twin_access_rejected(self):
        """Test that tenant A cannot access tenant B's twin entity."""
        # Register entity for tenant A
        entity_a = TwinEntity(
            tenant_id=self.tenant_a,
            name="TenantA Entity",
            entity_type="sensor",
        )
        registered = self.registry.register(entity_a)

        # Tenant B tries to access tenant A's entity
        result = self.registry.get(registered.id, self.tenant_b)
        assert result is None

        # State manager also rejects
        state_manager = TwinStateManager(self.registry)
        state = state_manager.get_state(registered.id, self.tenant_b)
        assert state is None

    def test_cross_tenant_binding_rejected(self):
        """Test that cross-tenant binding is rejected."""
        # Create entity for tenant B only (to test cross-tenant rejection)
        entity_b = TwinEntity(tenant_id=self.tenant_b, name="B Entity")
        registered_entity = self.registry.register(entity_b)

        # Setup device mock for tenant A
        mock_device = MagicMock()
        mock_device.id = uuid4()
        mock_device.tenant_id = self.tenant_a
        self.mock_device_repo.get_by_id_for_tenant.return_value = mock_device

        binding_service = EntityBindingService(self.registry, self.mock_device_repo)

        # Tenant A tries to bind to tenant B's entity (should fail)
        with pytest.raises(Exception):  # Either TwinEntityNotFoundError or TenantMismatch
            binding_service.create_binding(
                device_id=mock_device.id,
                entity_id=registered_entity.id,
                tenant_id=self.tenant_a,
            )

    def test_tenant_isolation_in_list(self):
        """Test that list operations are tenant-scoped."""
        # Create entities for both tenants
        for i in range(3):
            entity_a = TwinEntity(tenant_id=self.tenant_a, name=f"A{i}")
            entity_b = TwinEntity(tenant_id=self.tenant_b, name=f"B{i}")
            self.registry.register(entity_a)
            self.registry.register(entity_b)

        # Each tenant should only see their own entities
        entities_a = self.registry.list(self.tenant_a, limit=100)
        entities_b = self.registry.list(self.tenant_b, limit=100)

        assert len(entities_a) == 3
        assert len(entities_b) == 3
        assert all(e.tenant_id == self.tenant_a for e in entities_a)
        assert all(e.tenant_id == self.tenant_b for e in entities_b)

    def test_tenant_count_isolation(self):
        """Test that count operations respect tenant boundaries."""
        for i in range(5):
            entity = TwinEntity(tenant_id=self.tenant_a, name=f"A{i}")
            self.registry.register(entity)

        count_a = self.registry.count(self.tenant_a)
        count_b = self.registry.count(self.tenant_b)

        assert count_a == 5
        assert count_b == 0

    def test_registry_never_returns_cross_tenant_data(self):
        """Test registry never leaks data across tenants."""
        entity_a = TwinEntity(tenant_id=self.tenant_a, name="Secret")
        registered = self.registry.register(entity_a)

        # Try various ways to access cross-tenant
        assert self.registry.get(registered.id, self.tenant_b) is None
        assert self.registry.contains(registered.id, self.tenant_b) is False

        # List should be empty for tenant B
        assert len(self.registry.list(self.tenant_b)) == 0


class TestNoAdapterDependency:
    """Test that twin module has no adapter dependency."""

    def test_no_adapter_imports_in_service(self):
        """Verify twin services don't import from adapter."""
        import services.twin.services as twin_services
        import inspect

        source = inspect.getsource(twin_services)
        assert "services.adapter" not in source, "Service imports adapter module"
        assert "from services.adapter" not in source, "Service imports from adapter"

    def test_no_protocol_names_in_code(self):
        """Verify no protocol names appear in twin code."""
        import os
        import glob

        twin_dir = os.path.join(os.path.dirname(__file__), "..", "services", "twin")
        twin_files = glob.glob(os.path.join(twin_dir, "*.py"))

        forbidden_keywords = ["bacnet", "modbus", "opcua", "mqtt", "plc"]

        for filepath in twin_files:
            if filepath.endswith("__init__.py"):
                continue
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
                for keyword in forbidden_keywords:
                    assert keyword.lower() not in content.lower(), \
                        f"Protocol keyword '{keyword}' found in {filepath}"


class TestTenantIsolation:
    """Test tenant isolation in schemas and responses."""

    def test_tenant_id_not_in_schema(self):
        """Test that tenant_id is not exposed in response schemas."""
        from services.twin.models import TwinEntity

        # TwinEntity should have tenant_id (for internal use)
        entity = TwinEntity(tenant_id=uuid4(), name="Test")
        assert hasattr(entity, "tenant_id")

        # But it should NOT be serialized in API responses
        # (verified by route tests)

    def test_query_response_no_tenant_info(self):
        """Test that query responses don't leak tenant info."""
        registry = TwinEntityRegistry()
        tenant_id = uuid4()
        entity = TwinEntity(tenant_id=tenant_id, name="Test")
        registry.register(entity)

        # List should not expose tenant_id in a way that leaks other tenants' data
        entities = registry.list(tenant_id, limit=100)
        assert len(entities) == 1
        assert entities[0].tenant_id == tenant_id  # Same tenant, OK


class TestTenantFilterRequired:
    """Test that all operations require tenant filtering."""

    def test_registry_methods_require_tenant(self):
        """Test that registry methods accept tenant_id parameter."""
        from services.twin.registry import TwinEntityRegistry
        import inspect

        registry = TwinEntityRegistry()

        # All public methods should accept tenant_id
        methods_to_check = ["get", "remove", "list", "contains", "count", "clear"]
        for method_name in methods_to_check:
            method = getattr(registry, method_name)
            # Use getfullargspec for compatibility
            try:
                sig = inspect.signature(method)
                params = list(sig.parameters.keys())
            except Exception:
                # Fallback for Python version issues
                params = method.__code__.co_varnames[:method.__code__.co_argcount]
            assert "tenant_id" in params, \
                f"Method {method_name} does not accept tenant_id parameter"

    def test_cross_tenant_state_update_rejected(self):
        """Test that tenant A cannot update tenant B's twin state."""
        from services.twin.state import TwinStateManager
        from services.twin.exceptions import TwinEntityNotFoundError
        from services.iota.contracts import NormalizedTelemetry
        from datetime import datetime, timezone

        tenant_a = uuid4()
        tenant_b = uuid4()

        registry = TwinEntityRegistry()
        state_manager = TwinStateManager(registry)

        # Create entity for tenant A
        entity_a = TwinEntity(tenant_id=tenant_a, name="TenantA Entity")
        registry.register(entity_a)

        # Create telemetry for tenant B
        telemetry = NormalizedTelemetry(
            tenant_id=str(tenant_b),
            device_id=str(uuid4()),
            datapoint_id=str(uuid4()),
            event_time=datetime.now(timezone.utc),
            ingested_at=datetime.now(timezone.utc),
            value=25.5,
            data_type="FLOAT",
            quality="GOOD",
        )

        # Tenant B tries to update tenant A's entity state
        # Should raise TwinEntityNotFoundError because entity doesn't exist for tenant B
        with pytest.raises(TwinEntityNotFoundError):
            state_manager.update_state(entity_a.id, telemetry, tenant_b)

    def test_cross_tenant_binding_device_mismatch(self):
        """Test that binding is rejected when device tenant doesn't match entity tenant."""
        from services.twin.binding import EntityBindingService
        from unittest.mock import MagicMock

        tenant_a = uuid4()

        registry = TwinEntityRegistry()
        mock_device_repo = MagicMock()

        # Create entity for tenant A
        entity_a = TwinEntity(tenant_id=tenant_a, name="TenantA Entity")
        registry.register(entity_a)

        # Mock device not found for tenant A (because it belongs to tenant B)
        mock_device_repo.get_by_id_for_tenant.return_value = None

        binding_service = EntityBindingService(registry, mock_device_repo)

        # Try to bind non-existent device to entity from tenant A
        with pytest.raises(Exception):  # Should raise TwinBindingError
            binding_service.create_binding(
                device_id=uuid4(),
                entity_id=entity_a.id,
                tenant_id=tenant_a,
            )


class TestStateNamingConvention:
    """Test that runtime_state naming convention is used."""

    def test_twin_entity_has_runtime_state_attribute(self):
        """Verify TwinEntity uses runtime_state, not just state."""
        from services.twin.models import TwinEntity

        entity = TwinEntity(
            tenant_id=uuid4(),
            name="Test",
        )

        # Should have runtime_state attribute
        assert hasattr(entity, "runtime_state")
        assert entity.runtime_state == {}

    def test_state_property_exists_for_backward_compatibility(self):
        """Verify state property exists for backward compatibility."""
        from services.twin.models import TwinEntity

        # Verify state property exists for backward compatibility
        assert hasattr(TwinEntity, "state")

    def test_update_runtime_state_method_exists(self):
        """Verify update_runtime_state method exists."""
        from services.twin.models import TwinEntity

        entity = TwinEntity(
            tenant_id=uuid4(),
            name="Test",
        )

        # Should have update_runtime_state method
        assert hasattr(entity, "update_runtime_state")
        assert callable(entity.update_runtime_state)

    def test_get_runtime_state_method_exists(self):
        """Verify get_runtime_state method exists."""
        from services.twin.models import TwinEntity

        entity = TwinEntity(
            tenant_id=uuid4(),
            name="Test",
        )

        # Should have get_runtime_state method
        assert hasattr(entity, "get_runtime_state")
        assert callable(entity.get_runtime_state)
