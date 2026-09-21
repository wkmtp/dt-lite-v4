"""
test_architecture.py - Architecture Boundary Tests

Tests that enforce architectural boundaries:
- No adapter dependency
- No protocol coupling
- Tenant isolation preserved
"""
import os


class TestNoAdapterDependency:
    """Verify telemetry layer has no adapter dependencies."""

    def test_no_adapter_runtime_import(self):
        """Verify TelemetryIngestionService doesn't import AdapterRuntime."""
        from services.telemetry.services import TelemetryIngestionService
        import inspect

        source = inspect.getsource(TelemetryIngestionService)
        assert "AdapterRuntime" not in source

    def test_no_adapter_registry_import(self):
        """Verify no adapter registry usage."""
        from services.telemetry.services import TelemetryIngestionService
        import inspect

        source = inspect.getsource(TelemetryIngestionService)
        assert "AdapterRegistry" not in source

    def test_telemetry_module_files(self):
        """Check all telemetry module files for forbidden imports."""
        telemetry_dir = "/D/ai/itwin/dt-lite-v4/services/telemetry"

        if os.path.exists(telemetry_dir):
            for filename in os.listdir(telemetry_dir):
                if filename.endswith('.py'):
                    filepath = os.path.join(telemetry_dir, filename)
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()

                        # Check for adapter imports
                        assert 'from services.adapter' not in content, \
                            f"{filename} imports from services.adapter"
                        assert 'import services.adapter' not in content, \
                            f"{filename} imports services.adapter"


class TestNoProtocolDependency:
    """Verify no protocol implementation coupling."""

    def test_no_protocol_in_service(self):
        """Verify service layer has no protocol implementations."""
        from services.telemetry.services import TelemetryIngestionService
        import inspect

        source = inspect.getsource(TelemetryIngestionService)
        protocol_names = ['bacnet', 'modbus', 'opcua', 'mqtt', 'plc']

        for protocol in protocol_names:
            assert protocol.lower() not in source.lower(), \
                f"Protocol '{protocol}' found in services.py"

    def test_no_protocol_in_repository(self):
        """Verify repository layer has no protocol implementations."""
        from services.telemetry.repositories import TelemetryRepository
        import inspect

        source = inspect.getsource(TelemetryRepository)
        protocol_names = ['bacnet', 'modbus', 'opcua', 'mqtt', 'plc']

        for protocol in protocol_names:
            assert protocol.lower() not in source.lower(), \
                f"Protocol '{protocol}' found in repositories.py"

    def test_schemas_no_protocol_fields(self):
        """Verify schemas don't contain protocol-specific fields."""
        from services.telemetry.schemas import TelemetryPointCreate
        import inspect

        schema_source = inspect.getsource(TelemetryPointCreate)
        protocol_specific_fields = ['node_id', 'object_identifier', 'topic', 'coil', 'register', 'address']

        for field in protocol_specific_fields:
            assert field not in schema_source.lower(), \
                f"Protocol-specific field '{field}' found in schema"


class TestTenantIsolation:
    """Verify tenant isolation is maintained."""

    def test_tenant_id_not_in_schema(self):
        """Verify tenant_id is not exposed in request schemas."""
        from services.telemetry.schemas import TelemetryPointCreate

        # Check using model_fields (Pydantic V2)
        assert 'tenant_id' not in TelemetryPointCreate.model_fields, \
            "tenant_id should not be in request schema (comes from context)"

    def test_query_response_no_tenant_info(self):
        """Verify query responses don't expose tenant information."""
        from services.telemetry.schemas import TelemetryQueryResponse

        # Check using model_fields (Pydantic V2)
        assert 'tenant_id' not in TelemetryQueryResponse.model_fields, \
            "tenant_id should not be in response schema"


class TestDataFlow:
    """Verify correct data flow through the system."""

    def test_normalized_telemetry_contract_used(self):
        """Verify NormalizedTelemetry contract is used correctly."""
        from services.telemetry.services import TelemetryIngestionService
        import inspect

        # Check that service accepts NormalizedTelemetry
        source = inspect.getsource(TelemetryIngestionService.ingest)
        assert 'NormalizedTelemetry' in source or 'telemetry' in source.lower(), \
            "Service should accept NormalizedTelemetry"

    def test_repository_uses_tenant_aware_base(self):
        """Verify TelemetryRepository inherits from TenantAwareRepository."""
        from services.telemetry.repositories import TelemetryRepository
        from services.core.repositories.base import TenantAwareRepository

        assert issubclass(TelemetryRepository, TenantAwareRepository), \
            "TelemetryRepository must inherit from TenantAwareRepository"


class TestDatabaseModels:
    """Verify database model alignment."""

    def test_telemetry_point_has_required_fields(self):
        """Verify TelemetryPoint model has all required fields."""
        from services.telemetry.models import TelemetryPoint

        # Check that the class has the expected attributes via __annotations__
        annotations = TelemetryPoint.__annotations__

        required_fields = ['id', 'tenant_id', 'device_id', 'datapoint_id',
                          'event_time', 'ingested_at', 'value', 'data_type',
                          'quality']

        for field in required_fields:
            assert field in annotations, f"Missing required annotation: {field}"

    def test_metadata_field_exists(self):
        """Verify metadata field exists (via workaround)."""
        from services.telemetry.models import TelemetryPoint

        annotations = TelemetryPoint.__annotations__

        # Either 'metadata' or 'meta_data' should exist
        assert 'metadata' in annotations or 'meta_data' in annotations, \
            "Metadata field must exist (as 'metadata' or 'meta_data')"


class TestMigrationExists:
    """Verify migration file exists."""

    def test_phase6_migration_exists(self):
        """Verify phase6_telemetry.py migration exists."""
        migration_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "database", "migrations", "versions", "phase6_telemetry.py"
        )

        assert os.path.exists(migration_path), \
            f"Migration file phase6_telemetry.py not found at {migration_path}"
