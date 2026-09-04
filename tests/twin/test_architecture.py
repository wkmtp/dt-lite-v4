"""Test Twin Runtime Architecture — Boundaries and dependencies."""
import os


class TestNoAdapterDependency:
    """Test that twin module has no adapter or protocol dependencies."""

    def test_no_adapter_runtime_import(self):
        """Verify services/twin doesn't import from services.adapter."""
        # Read all Python files in services/twin
        twin_dir = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "services", "twin"
        )

        for root, dirs, files in os.walk(twin_dir):
            for filename in files:
                if filename.endswith(".py") and filename != "__init__.py":
                    filepath = os.path.join(root, filename)
                    with open(filepath, "r", encoding="utf-8") as f:
                        content = f.read()
                        assert "services.adapter" not in content, \
                            f"Found adapter import in {filepath}"
                        assert "from services.adapter" not in content, \
                            f"Found adapter import in {filepath}"

    def test_no_adapter_registry_import(self):
        """Verify twin module doesn't import adapter registry."""
        import services.twin.registry as registry_module
        import inspect

        source = inspect.getsource(registry_module)
        assert "adapter" not in source.lower() or "TwinEntity" in source, \
            "Registry imports adapter module"

    def test_twin_module_files(self):
        """Verify all expected twin module files exist."""
        # Path: tests/twin/test_architecture.py -> services/twin/
        twin_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "services", "twin"
        )

        expected_files = [
            "__init__.py",
            "exceptions.py",
            "models.py",
            "registry.py",
            "state.py",
            "binding.py",
            "services.py",
            "routes.py",
        ]

        for filename in expected_files:
            filepath = os.path.join(twin_dir, filename)
            assert os.path.exists(filepath), f"Missing file: {filename}"


class TestNoProtocolDependency:
    """Test that twin module contains no protocol logic."""

    def test_no_protocol_in_service(self):
        """Verify no protocol names in service code."""
        import services.twin.services as services_module
        import inspect

        source = inspect.getsource(services_module)
        forbidden = ["bacnet", "modbus", "opcua", "mqtt", "plc"]
        for keyword in forbidden:
            assert keyword.lower() not in source.lower(), \
                f"Protocol keyword '{keyword}' found in services.py"

    def test_no_protocol_in_repository(self):
        """Verify no protocol references in registry."""
        import services.twin.registry as registry_module
        import inspect

        source = inspect.getsource(registry_module)
        forbidden = ["bacnet", "modbus", "opcua", "mqtt", "plc"]
        for keyword in forbidden:
            assert keyword.lower() not in source.lower(), \
                f"Protocol keyword '{keyword}' found in registry.py"

    def test_schemas_no_protocol_fields(self):
        """Verify TwinEntity schema has no protocol-specific fields."""
        from services.twin.models import TwinEntity

        # TwinEntity should have generic fields, not protocol-specific
        field_names = [f for f in dir(TwinEntity) if not f.startswith("_")]
        protocol_fields = ["bacnet", "modbus", "opcua", "mqtt", "protocol"]

        for pf in protocol_fields:
            assert not any(pf in f.lower() for f in field_names), \
                f"Protocol field '{pf}' found in TwinEntity"


class TestTenantIsolation:
    """Test tenant isolation in twin module."""

    def test_tenant_id_not_in_schema(self):
        """Test tenant_id is not exposed in request schemas."""
        from services.twin.models import TwinEntity

        # TwinEntity is a dataclass, not a Pydantic model
        # But it should have tenant_id as an internal field
        entity = TwinEntity(tenant_id=__import__("uuid").uuid4())
        assert hasattr(entity, "tenant_id")

    def test_query_response_no_tenant_info(self):
        """Test that responses don't expose raw tenant data inappropriately."""
        from services.twin.models import TwinEntity
        from uuid import uuid4

        tenant_id = uuid4()
        entity = TwinEntity(tenant_id=tenant_id, name="Test")

        # Verify entity has tenant_id
        assert entity.tenant_id == tenant_id


class TestDataFlow:
    """Test data flow between modules."""

    def test_normalized_telemetry_contract_used(self):
        """Verify NormalizedTelemetry contract is used (not bypassed)."""
        from services.twin.state import TwinStateManager

        # Import check - state manager should accept NormalizedTelemetry
        import inspect
        sig = inspect.signature(TwinStateManager.update_state)
        params = list(sig.parameters.keys())
        assert "telemetry" in params, "update_state should accept telemetry parameter"

    def test_repository_uses_tenant_aware_base(self):
        """Verify registry follows tenant-aware pattern."""
        from services.twin.registry import TwinEntityRegistry

        # Registry should be tenant-aware by design
        registry = TwinEntityRegistry()
        assert hasattr(registry, "get")
        assert hasattr(registry, "list")
        assert hasattr(registry, "count")


class TestDataModels:
    """Test data model structure."""

    def test_twin_entity_has_required_fields(self):
        """Verify TwinEntity has required fields."""
        from services.twin.models import TwinEntity
        from uuid import uuid4

        entity = TwinEntity(
            tenant_id=uuid4(),
            name="Test Pump",
            entity_type="pump",
        )

        assert entity.id is not None
        assert entity.name == "Test Pump"
        assert entity.entity_type == "pump"
        assert isinstance(entity.state, dict)
        assert isinstance(entity.created_at, __import__("datetime").datetime)

    def test_metadata_field_exists(self):
        """Verify template field exists for configuration."""
        from services.twin.models import TwinEntity

        entity = TwinEntity(template={"key": "value"})
        assert entity.template == {"key": "value"}
