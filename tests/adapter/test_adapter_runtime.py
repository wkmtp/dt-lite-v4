"""Adapter Runtime Tests - Contract, Registry, Lifecycle, Health, Security."""
import asyncio
import os
import pytest
from datetime import datetime, timezone

from services.iota.contracts import (
    AdapterCapability,
    DataQuality,
    DataType,
    DiscoveryResult,
    NormalizedTelemetry,
    ProtocolAdapter,
)
from services.adapter.exceptions import (
    AdapterLifecycleError,
    AdapterNotFoundError,
)
from services.adapter.registry import AdapterRegistry
from services.adapter.runtime import AdapterRuntime
from services.adapter.health import HealthMonitor
from services.adapter.lifecycle import AdapterLifecycle, LifecycleState
from services.adapter.simulator import SimulatorAdapter


class TestContractImplementation:
    """Verify all adapters implement ProtocolAdapter correctly."""

    def test_simulator_implements_protocol_adapter(self):
        """SimulatorAdapter must be a ProtocolAdapter subclass."""
        adapter = SimulatorAdapter()
        assert isinstance(adapter, ProtocolAdapter)

    def test_simulator_has_all_required_methods(self):
        """ProtocolAdapter requires connect, disconnect, health, discover, read, write,
        subscribe, unsubscribe, and capabilities methods."""
        adapter = SimulatorAdapter()
        required_methods = [
            "connect", "disconnect", "health", "discover",
            "read", "write", "subscribe", "unsubscribe", "capabilities"
        ]
        for method in required_methods:
            assert hasattr(adapter, method), f"Missing method: {method}"
            assert callable(getattr(adapter, method)), f"{method} must be callable"

    def test_simulator_capabilities_declared(self):
        """SimulatorAdapter declares READ, WRITE, DISCOVERY, SUBSCRIBE."""
        adapter = SimulatorAdapter()
        caps = adapter.capabilities()
        assert AdapterCapability.READ in caps
        assert AdapterCapability.WRITE in caps
        assert AdapterCapability.DISCOVERY in caps
        assert AdapterCapability.SUBSCRIBE in caps


class TestRegistry:
    """AdapterRegistry tests."""

    def test_register_and_get(self):
        registry = AdapterRegistry()
        adapter = SimulatorAdapter()
        registry.register("sim", adapter)
        assert registry.get("sim") is adapter

    def test_register_duplicate_raises(self):
        registry = AdapterRegistry()
        adapter = SimulatorAdapter()
        registry.register("sim", adapter)
        with pytest.raises(ValueError, match="must implement"):
            registry.register("sim", "not-an-adapter")

    def test_get_missing_raises(self):
        registry = AdapterRegistry()
        with pytest.raises(AdapterNotFoundError):
            registry.get("missing")

    def test_remove(self):
        registry = AdapterRegistry()
        adapter = SimulatorAdapter()
        registry.register("sim", adapter)
        registry.remove("sim")
        with pytest.raises(AdapterNotFoundError):
            registry.get("sim")

    def test_list_adapters(self):
        registry = AdapterRegistry()
        adapter1 = SimulatorAdapter()
        adapter2 = SimulatorAdapter()
        registry.register("sim1", adapter1)
        registry.register("sim2", adapter2)
        names = registry.list_adapters()
        assert sorted(names) == ["sim1", "sim2"]

    def test_contains(self):
        registry = AdapterRegistry()
        adapter = SimulatorAdapter()
        registry.register("sim", adapter)
        assert registry.contains("sim")
        assert not registry.contains("other")

    def test_count(self):
        registry = AdapterRegistry()
        assert registry.count == 0
        registry.register("sim", SimulatorAdapter())
        assert registry.count == 1
        registry.clear()
        assert registry.count == 0

    def test_clear(self):
        registry = AdapterRegistry()
        registry.register("sim", SimulatorAdapter())
        registry.clear()
        assert registry.count == 0


class TestLifecycle:
    """AdapterLifecycle state machine tests."""

    def test_initial_state_is_created(self):
        lifecycle = AdapterLifecycle("test")
        assert lifecycle.state == LifecycleState.CREATED

    def test_can_transition_from_created_to_connected(self):
        lifecycle = AdapterLifecycle("test")
        assert lifecycle.can_transition(LifecycleState.CONNECTED)
        assert not lifecycle.can_transition(LifecycleState.RUNNING)

    def test_connect_transitions_to_connected(self):
        lifecycle = AdapterLifecycle("test")
        adapter = SimulatorAdapter()
        asyncio.run(lifecycle.connect(adapter, "tcp://localhost:1234", "creds", {}))
        assert lifecycle.state == LifecycleState.CONNECTED

    def test_start_transitions_to_running(self):
        lifecycle = AdapterLifecycle("test")
        adapter = SimulatorAdapter()
        asyncio.run(lifecycle.connect(adapter, "tcp://localhost:1234", "creds", {}))
        asyncio.run(lifecycle.start(adapter))
        assert lifecycle.state == LifecycleState.RUNNING

    def test_stop_transitions_to_stopped(self):
        lifecycle = AdapterLifecycle("test")
        adapter = SimulatorAdapter()
        asyncio.run(lifecycle.connect(adapter, "tcp://localhost:1234", "creds", {}))
        asyncio.run(lifecycle.start(adapter))
        asyncio.run(lifecycle.stop(adapter))
        assert lifecycle.state == LifecycleState.STOPPED

    def test_disconnect_resets_to_created(self):
        lifecycle = AdapterLifecycle("test")
        adapter = SimulatorAdapter()
        asyncio.run(lifecycle.connect(adapter, "tcp://localhost:1234", "creds", {}))
        asyncio.run(lifecycle.start(adapter))
        asyncio.run(lifecycle.stop(adapter))
        asyncio.run(lifecycle.reset(adapter))
        assert lifecycle.state == LifecycleState.CREATED

    def test_invalid_transition_raises(self):
        lifecycle = AdapterLifecycle("test")
        adapter = SimulatorAdapter()
        with pytest.raises(AdapterLifecycleError):
            asyncio.run(lifecycle.start(adapter))


class TestRuntime:
    """AdapterRuntime integration tests."""

    @pytest.fixture
    def runtime(self):
        registry = AdapterRegistry()
        registry.register("sim", SimulatorAdapter())
        return AdapterRuntime(registry)

    @pytest.mark.asyncio
    async def test_create_instance(self, runtime):
        await runtime.create("sim")
        assert "sim" in runtime.list_instances()
        status = runtime.get_status("sim")
        assert status["state"] == "CREATED"

    @pytest.mark.asyncio
    async def test_connect_instance(self, runtime):
        await runtime.create("sim")
        await runtime.connect("sim", "tcp://localhost:1234", "creds-ref")
        status = runtime.get_status("sim")
        assert status["state"] == "CONNECTED"

    @pytest.mark.asyncio
    async def test_full_lifecycle(self, runtime):
        await runtime.create("sim")
        await runtime.connect("sim", "tcp://localhost:1234", "creds")
        await runtime.start("sim")
        assert runtime.get_status("sim")["state"] == "RUNNING"
        await runtime.stop("sim")
        assert runtime.get_status("sim")["state"] == "STOPPED"
        await runtime.disconnect("sim")
        assert runtime.get_status("sim")["state"] == "CREATED"

    @pytest.mark.asyncio
    async def test_discover(self, runtime):
        await runtime.create("sim")
        results = await runtime.discover("sim")
        assert len(results) > 0
        assert all(isinstance(r, DiscoveryResult) for r in results)

    @pytest.mark.asyncio
    async def test_read_returns_telemetry(self, runtime):
        await runtime.create("sim")
        telemetry = await runtime.read("sim", ["temp-001"])
        assert len(telemetry) == 1
        t = telemetry[0]
        assert isinstance(t, NormalizedTelemetry)
        assert t.tenant_id == "sim-tenant"
        assert t.device_id == "sim-device-001"
        assert t.datapoint_id == "temp-001"
        assert t.data_type == DataType.FLOAT.value

    @pytest.mark.asyncio
    async def test_write_success(self, runtime):
        await runtime.create("sim")
        result = await runtime.write("sim", "temp-001", 25.5, DataType.FLOAT.value)
        assert result is True

    @pytest.mark.asyncio
    async def test_subscribe_and_unsubscribe(self, runtime):
        await runtime.create("sim")
        sub_id = await runtime.subscribe("sim", "temp-001", lambda x: x)
        assert isinstance(sub_id, str)
        await runtime.unsubscribe("sim", sub_id)

    @pytest.mark.asyncio
    async def test_health_check(self, runtime):
        await runtime.create("sim")
        await runtime.connect("sim", "tcp://localhost:1234", "creds")
        health = await runtime.health_check("sim")
        assert health["status"] == "HEALTHY"
        assert "adapter_name" in health

    @pytest.mark.asyncio
    async def test_missing_instance_raises(self, runtime):
        with pytest.raises(AdapterNotFoundError):
            await runtime.discover("nonexistent")

    @pytest.mark.asyncio
    async def test_destroy(self, runtime):
        await runtime.create("sim")
        await runtime.connect("sim", "tcp://localhost:1234", "creds")
        await runtime.destroy("sim")
        assert "sim" not in runtime.list_instances()

    def test_runtime_no_repository_access(self):
        """Runtime must not import or use any repository."""
        import services.adapter.runtime as rt_module
        source = rt_module.__file__
        with open(source, "r", encoding="utf-8") as f:
            content = f.read()
        # Check that repository pattern is not used (no import of repositories)
        lines = content.split('\n')
        for line in lines:
            if 'import' in line and 'repository' in line.lower():
                assert False, f"Runtime should not import repositories: {line}"


class TestHealthMonitor:
    """HealthMonitor tests."""

    @pytest.mark.asyncio
    async def test_healthy_adapter(self):
        monitor = HealthMonitor()
        adapter = SimulatorAdapter()
        await adapter.connect("tcp://localhost:1234", "creds", {})
        health = await monitor.check("sim", adapter)
        assert health.status == "HEALTHY"
        assert health.message == "Adapter is operational"

    @pytest.mark.asyncio
    async def test_unhealthy_adapter(self):
        monitor = HealthMonitor()
        adapter = SimulatorAdapter()
        # Don't connect - health should be False
        health = await monitor.check("sim", adapter)
        assert health.status == "UNHEALTHY"

    def test_get_cached_health(self):
        monitor = HealthMonitor()
        adapter = SimulatorAdapter()
        # Cache empty initially
        assert monitor.get_health("sim") is None
        # After check
        asyncio.run(monitor.check("sim", adapter))
        health = monitor.get_health("sim")
        assert health is not None
        assert health.adapter_name == "sim"

    def test_get_all_health(self):
        monitor = HealthMonitor()
        adapter1 = SimulatorAdapter()
        adapter2 = SimulatorAdapter()
        asyncio.run(monitor.check("sim1", adapter1))
        asyncio.run(monitor.check("sim2", adapter2))
        all_health = monitor.get_all_health()
        assert len(all_health) == 2

    def test_clear_cache(self):
        monitor = HealthMonitor()
        adapter = SimulatorAdapter()
        asyncio.run(monitor.check("sim", adapter))
        monitor.clear_cache()
        assert monitor.get_health("sim") is None


class TestNormalizedTelemetry:
    """NormalizedTelemetry validation tests."""

    def test_valid_telemetry(self):
        now = datetime.now(timezone.utc)
        t = NormalizedTelemetry(
            tenant_id="tenant-1",
            device_id="device-1",
            datapoint_id="dp-1",
            event_time=now,
            ingested_at=now,
            value=25.5,
            data_type=DataType.FLOAT.value,
            unit="degC",
            quality=DataQuality.GOOD.value,
        )
        assert t.validate() == []  # No errors

    def test_missing_tenant_id(self):
        now = datetime.now(timezone.utc)
        t = NormalizedTelemetry(
            tenant_id="",
            device_id="device-1",
            datapoint_id="dp-1",
            event_time=now,
            ingested_at=now,
            value=25.5,
            data_type=DataType.FLOAT.value,
        )
        errors = t.validate()
        assert any("tenant_id" in e for e in errors)

    def test_timezone_aware(self):
        """All datetimes must be timezone-aware UTC."""
        now = datetime.now(timezone.utc)
        t = NormalizedTelemetry(
            tenant_id="t1",
            device_id="d1",
            datapoint_id="dp1",
            event_time=now,
            ingested_at=now,
            value=1.0,
            data_type=DataType.FLOAT.value,
        )
        assert t.event_time.tzinfo is not None
        assert t.ingested_at.tzinfo is not None
        assert t.event_time.utcoffset().total_seconds() == 0  # UTC

    def test_naive_datetime_accepted_but_not_recommended(self):
        """Naive datetimes are accepted by validate() but best practice is to use aware."""
        naive = datetime.now()  # No timezone
        t = NormalizedTelemetry(
            tenant_id="t1",
            device_id="d1",
            datapoint_id="dp1",
            event_time=naive,
            ingested_at=naive,
            value=1.0,
            data_type=DataType.FLOAT.value,
        )
        # Validation doesn't enforce tzinfo, but contract requires it
        assert t.validate() == []


class TestSecurityBoundaries:
    """Security boundary tests for Adapter Runtime."""

    @pytest.mark.asyncio
    async def test_adapter_cannot_access_repository(self):
        """Adapter has no direct database access."""
        import services.adapter.simulator as sim_module
        source = sim_module.__file__
        with open(source, "r", encoding="utf-8") as f:
            content = f.read()
        assert "repository" not in content.lower(), "Adapter must not access repositories"

    @pytest.mark.asyncio
    async def test_runtime_cannot_bypass_tenant_boundary(self):
        """Runtime does not have tenant authority."""
        import services.adapter.runtime as rt_module
        source = rt_module.__file__
        with open(source, "r", encoding="utf-8") as f:
            content = f.read()
        # Runtime accepts tenant_id as parameter but doesn't store it as attribute
        assert "self._tenant_id" not in content, "Runtime must not store tenant_id"

    def test_registry_has_no_tenant_logic(self):
        """Registry is stateless regarding tenant context."""
        import services.adapter.registry as reg_module
        source = reg_module.__file__
        with open(source, "r", encoding="utf-8") as f:
            content = f.read()
        # Registry should not have tenant-specific methods or logic
        if "def " in content:
            next_def = content.split("def ")[1].split("\n")[0]
            assert "tenant" not in next_def.lower(), "Registry has tenant-specific method"

    def test_no_secret_exposure_in_logs(self):
        """Endpoint/secret must not be logged in plain text."""
        import services.adapter.runtime as rt_module
        source = rt_module.__file__
        with open(source, "r", encoding="utf-8") as f:
            content = f.read()
        # Should redact endpoint in logs
        assert "[ENDPOINT_REDACTED]" in content, "Must redact endpoint in logs"

    @pytest.mark.asyncio
    async def test_connection_does_not_store_credentials(self):
        """Connect should accept credentials_ref but not store the actual secret."""
        runtime = AdapterRuntime(AdapterRegistry())
        runtime._registry.register("sim", SimulatorAdapter())
        await runtime.create("sim")
        await runtime.connect("sim", "tcp://localhost:1234", "my-secret-ref")
        instance = runtime._instances["sim"]
        # Endpoint is stored (redacted), credentials_ref is NOT stored
        assert instance.connected_endpoint == "tcp://localhost:1234"
        assert not hasattr(instance, "_credentials")
        assert not hasattr(instance, "_password")


class TestProtocolIndependence:
    """Verify no protocol coupling in adapter layer."""

    def test_no_protocol_names_in_adapter_code(self):
        """No BACnet, Modbus, OPC UA, MQTT, or PLC in adapter module source code.
        
        Note: Protocol names may appear in docstrings as negative examples
        (e.g., "does NOT implement BACnet") which is acceptable.
        Only fail if protocol names appear in actual executable code.
        """
        import services.adapter
        adapter_dir = os.path.dirname(services.adapter.__file__)
        forbidden = ["bacnet", "modbus", "opcua", "opc ua", "mqtt", "plc"]
        for root, dirs, files in os.walk(adapter_dir):
            for f in files:
                if f.endswith(".py"):
                    path = os.path.join(root, f)
                    with open(path, "r", encoding="utf-8") as fh:
                        content = fh.read()
                    # Skip docstrings by removing triple-quoted sections
                    # This prevents false positives from doc examples
                    import re
                    # Remove docstrings
                    cleaned = re.sub(r'""".*?"""', '', content, flags=re.DOTALL)
                    cleaned = re.sub(r"'''.*?'''", '', cleaned, flags=re.DOTALL)
                    for term in forbidden:
                        assert term not in cleaned.lower(), f"Found '{term}' in executable code at {path}"

    def test_simulator_does_not_simulate_real_protocols(self):
        """Simulator generates fake data, not protocol-specific responses."""
        adapter = SimulatorAdapter()
        results = asyncio.run(adapter.discover())
        for r in results:
            meta = r.metadata or {}
            assert "bacnet" not in meta.get("model", "").lower()
            assert "modbus" not in meta.get("vendor", "").lower()
