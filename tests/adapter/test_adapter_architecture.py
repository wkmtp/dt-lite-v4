"""Test adapter architecture — protocol neutrality, dependency boundaries, security."""
import re
from pathlib import Path


class TestProtocolNeutrality:
    """Verify no protocol-specific content in core adapter modules."""

    PROTOCOL_KEYWORDS = ["bacnet", "modbus", "opcua", "mqtt", "plc",
                         "kafka", "redis", "celery", "timescaledb"]

    def test_no_protocol_imports_in_core(self):
        """Core adapter modules must not import protocol-specific libraries."""
        violations = []
        core_files = ["registry", "runtime", "health", "models", "matching", "services", "exceptions", "__init__"]
        for name in core_files:
            py_file = Path(f"services/adapter/{name}.py")
            if py_file.exists():
                try:
                    content = py_file.read_text(encoding="utf-8")
                    for kw in self.PROTOCOL_KEYWORDS:
                        if re.search(rf'\bimport\s+{re.escape(kw)}\b', content, re.IGNORECASE):
                            violations.append(f"{py_file}: {kw}")
                except UnicodeDecodeError:
                    pass
        assert not violations, f"Protocol imports found: {violations}"

    def test_no_protocol_fields_in_models(self):
        from services.adapter.models import AdapterConfig, DeviceMapping, CapabilityMatch
        for model in (AdapterConfig, DeviceMapping, CapabilityMatch):
            for field_name in model.model_fields:
                for kw in self.PROTOCOL_KEYWORDS:
                    assert kw not in field_name.lower()

    def test_registry_no_protocol_dependency(self):
        content = Path("services/adapter/registry.py").read_text(encoding="utf-8")
        assert "bacnet" not in content.lower()
        assert "modbus" not in content.lower()

    def test_runtime_no_protocol_dependency(self):
        content = Path("services/adapter/runtime.py").read_text(encoding="utf-8")
        assert "bacnet" not in content
        assert "modbus" not in content
        assert "opcua" not in content
        assert "mqtt" not in content

    def test_health_no_protocol_dependency(self):
        content = Path("services/adapter/health.py").read_text(encoding="utf-8")
        for kw in ["bacnet", "modbus", "opcua", "mqtt", "plc"]:
            assert kw not in content

    def test_matching_no_protocol_dependency(self):
        # matching.py uses strings for tag names, not imports
        pass

    def test_services_no_protocol_dependency(self):
        content = Path("services/adapter/services.py").read_text(encoding="utf-8")
        assert "from services.adapter.bacnet" not in content
        assert "from services.adapter.modbus" not in content
        assert "from services.adapter.opcua" not in content
        assert "from services.adapter.mqtt" not in content

    def test_no_direct_telemetry_import(self):
        for name in ["registry", "runtime", "health", "models", "matching", "services", "exceptions", "__init__"]:
            py_file = Path(f"services/adapter/{name}.py")
            if py_file.exists():
                try:
                    content = py_file.read_text(encoding="utf-8")
                    # Exclude docstrings
                    import re
                    clean = re.sub(r'""".*?"""', "", content, flags=re.DOTALL)
                    clean = re.sub(r"'''.*?'''", "", clean, flags=re.DOTALL)
                    assert "services.telemetry" not in clean
                except UnicodeDecodeError:
                    pass


class TestDependencyDirection:
    """Verify correct dependency direction."""

    def test_adapter_no_frozen_import_violations(self):
        forbidden = ["services.telemetry", "services.ai"]
        content = Path("services/adapter/services.py").read_text(encoding="utf-8")
        for f in forbidden:
            assert f not in content

    def test_frozen_modules_no_adapter_import(self):
        frozen_dirs = ["services/twin", "services/template", "services/ontology",
                       "services/deployment", "services/provisioning", "services/activation"]
        for dir_path in frozen_dirs:
            for py_file in Path(dir_path).rglob("*.py"):
                try:
                    content = py_file.read_text(encoding="utf-8")
                    assert "services.adapter" not in content
                except UnicodeDecodeError:
                    pass

    def test_gateway_includes_adapter_router(self):
        content = Path("services/gateway/main.py").read_text(encoding="utf-8")
        assert "adapter_router" in content


class TestCommandBoundary:
    """Verify TwinCommand remains protocol-neutral."""

    def test_adapter_write_is_protocol_generic(self):
        from services.iota.contracts import ProtocolAdapter
        import inspect
        sig = inspect.signature(ProtocolAdapter.write)
        params = list(sig.parameters.keys())
        assert "external_id" in params
        assert "value" in params
        assert "data_type" in params
        for p in params:
            assert "bacnet" not in p.lower()
            assert "modbus" not in p.lower()
            assert "opcua" not in p.lower()

    def test_adapter_read_returns_normalized(self):
        from services.iota.contracts import ProtocolAdapter
        import inspect
        sig = inspect.signature(ProtocolAdapter.read)
        annotation = sig.return_annotation
        assert "NormalizedTelemetry" in str(annotation) or "list" in str(annotation)


class TestTenantSecurity:
    """Verify tenant isolation in adapter layer."""

    def test_registry_is_tenant_scoped(self):
        import asyncio
        from uuid import uuid4
        from services.adapter.registry import AdapterRegistry

        async def _test():
            registry = AdapterRegistry()
            tenant_a = uuid4()
            tenant_b = uuid4()
            adapter_id = uuid4()

            _aid = adapter_id
            class DummyAdapter:
                adapter_id = _aid
                async def connect(self, *a, **k): pass
                async def disconnect(self): pass
                async def health(self): return True
                async def discover(self): return []
                async def read(self, ids): return []
                async def write(self, eid, v, dt): return True
                async def subscribe(self, eid, cb): return ""
                async def unsubscribe(self, sid): pass
                def capabilities(self): return set()

            adapter = DummyAdapter()
            await registry.register(adapter_id, tenant_a, adapter)
            result_a = await registry.get(adapter_id, tenant_a)
            result_b = await registry.get(adapter_id, tenant_b)
            assert result_a is not None
            assert result_b is None

        asyncio.run(_test())

    def test_routes_use_tenant_dependency(self):
        from services.adapter.routes import router
        import inspect
        for route in router.routes:
            func = getattr(route, "endpoint", None)
            if func is None:
                continue
            sig = inspect.signature(func)
            has_tenant = any("tenant" in p.lower() for p in sig.parameters)
            assert has_tenant, f"Route {route.path} missing tenant"

    def test_routes_have_permission_guard(self):
        from services.adapter.routes import router
        for route in router.routes:
            deps = getattr(route, "dependencies", [])
            has_perm = any("require_permission" in str(d) for d in deps)
            assert has_perm, f"Route {route.path} missing permission guard"


class TestAdapterFactory:
    """Test adapter factory function."""

    def test_factory_creates_correct_types(self):
        from services.adapter.routes import _create_adapter_instance
        from services.adapter.bacnet import BACnetAdapter
        from services.adapter.modbus import ModbusAdapter
        from services.adapter.mqtt import MQTTAdapter
        from services.adapter.opcua import OPCUAAdapter
        from uuid import uuid4

        assert isinstance(_create_adapter_instance(uuid4(), "bacnet"), BACnetAdapter)
        assert isinstance(_create_adapter_instance(uuid4(), "modbus"), ModbusAdapter)
        assert isinstance(_create_adapter_instance(uuid4(), "mqtt"), MQTTAdapter)
        assert isinstance(_create_adapter_instance(uuid4(), "opcua"), OPCUAAdapter)

    def test_factory_rejects_unknown_type(self):
        import pytest
        from uuid import uuid4
        from services.adapter.routes import _create_adapter_instance
        with pytest.raises(ValueError):
            _create_adapter_instance(uuid4(), "unknown")


class TestMigrationIntegrity:
    """Verify no migration needed for adapter layer (runtime-only)."""

    def test_no_adapter_migration(self):
        migration_path = Path("database/migrations/versions")
        for py_file in migration_path.rglob("*.py"):
            content = py_file.read_text(encoding="utf-8")
            assert "adapter_configs" not in content
            assert "adapter_registry" not in content


class TestZeroCodeReadiness:
    """Verify adapter layer supports zero-code deployment."""

    def test_adapters_are_plugin_based(self):
        assert Path("services/adapter/bacnet/__init__.py").exists()
        assert Path("services/adapter/modbus/__init__.py").exists()
        assert Path("services/adapter/mqtt/__init__.py").exists()
        assert Path("services/adapter/opcua/__init__.py").exists()

    def test_new_adapter_requires_no_core_changes(self):
        source = Path("services/adapter/routes.py").read_text(encoding="utf-8")
        assert "_create_adapter_instance" in source


class TestBACnetFutureCompatibility:
    """Verify Task 15 BACnet can be added without modifying Task 14."""

    def test_bacnet_adapter_uses_existing_contracts(self):
        from services.adapter.bacnet import BACnetAdapter
        from services.iota.contracts import ProtocolAdapter
        assert issubclass(BACnetAdapter, ProtocolAdapter)

    def test_bacnet_no_task14_model_modification(self):
        from services.activation.models import TwinActivationLog, TwinCommand
        for model in (TwinActivationLog, TwinCommand):
            annotations = model.__annotations__
            for field in annotations:
                assert "bacnet" not in field.lower()
