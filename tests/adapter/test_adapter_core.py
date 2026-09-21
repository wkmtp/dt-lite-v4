"""Test adapter core — contracts, registry, runtime, health, matching."""
import asyncio
import pytest
from uuid import uuid4

from services.iota.contracts import (
    ProtocolAdapter,
    AdapterCapability,
    NormalizedTelemetry,
    DataType,
    DataQuality,
)
from services.adapter.exceptions import (
    AdapterError,
    AdapterConnectionError,
    AdapterNotFoundError,
    AdapterAlreadyExistsError,
    AdapterNotConnectedError,
    AdapterCapabilityMismatchError,
)
from services.adapter.registry import AdapterRegistry
from services.adapter.runtime import AdapterRuntime, CircuitBreaker
from services.adapter.health import AdapterHealthChecker, AdapterHealthStatus
from services.adapter.matching import CapabilityAdapterMatcher
from services.adapter.models import AdapterConfig, CapabilityMatch, DeviceMapping


class MockAdapter(ProtocolAdapter):
    """Mock adapter for testing."""

    def __init__(self, adapter_id):
        self._adapter_id = adapter_id
        self._connected = False
        self._read_count = 0
        self._write_count = 0
        self._sub_count = 0

    @property
    def adapter_id(self):
        return self._adapter_id

    async def connect(self, endpoint, credentials_ref, config):
        self._connected = True
        self._endpoint = endpoint

    async def disconnect(self):
        self._connected = False
        self._client = None

    async def health(self):
        return self._connected

    async def discover(self):
        return []

    async def read(self, external_ids):
        self._read_count += 1
        return [
            NormalizedTelemetry(
                tenant_id="test", device_id=str(self._adapter_id),
                datapoint_id=ext_id,
                event_time=__import__("datetime").datetime.now(__import__("datetime").timezone.utc),
                ingested_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc),
                value=22.5, data_type="FLOAT", quality="GOOD",
            )
            for ext_id in external_ids
        ]

    async def write(self, external_id, value, data_type):
        self._write_count += 1
        return True

    async def subscribe(self, external_id, callback):
        self._sub_count += 1
        return f"sub_{external_id}"

    async def unsubscribe(self, subscription_id):
        pass

    def capabilities(self):
        return {
            AdapterCapability.READ,
            AdapterCapability.WRITE,
            AdapterCapability.DISCOVERY,
            AdapterCapability.SUBSCRIBE,
        }


class TestProtocolAdapterContract:
    """Test ProtocolAdapter abstract base class."""

    def test_abstract_methods(self):
        """All required methods must be defined."""
        required = {
            "connect", "disconnect", "health", "discover",
            "read", "write", "subscribe", "unsubscribe", "capabilities",
        }
        abstract_methods = set(ProtocolAdapter.__abstractmethods__)
        assert required.issubset(abstract_methods)

    def test_normalized_telemetry_validation(self):
        """NormalizedTelemetry must validate required fields."""
        from datetime import datetime, timezone
        telemetry = NormalizedTelemetry(
            tenant_id="tenant-1",
            device_id="device-1",
            datapoint_id="dp-1",
            event_time=datetime.now(timezone.utc),
            ingested_at=datetime.now(timezone.utc),
            value=22.5,
            data_type="FLOAT",
            quality="GOOD",
        )
        assert telemetry.validate() == []

    def test_normalized_telemetry_missing_fields(self):
        """NormalizedTelemetry with missing fields should fail validation."""
        telemetry = NormalizedTelemetry(
            tenant_id="", device_id="", datapoint_id="",
            event_time=None, ingested_at=None,
            value=None, data_type="INVALID", quality="BAD",
        )
        errors = telemetry.validate()
        assert len(errors) > 0

    def test_adapter_capability_enum(self):
        """AdapterCapability enum must have correct values."""
        caps = {c.value for c in AdapterCapability}
        assert caps == {"READ", "WRITE", "DISCOVERY", "SUBSCRIBE"}

    def test_data_type_enum(self):
        """DataType enum must have correct values."""
        types = {t.value for t in DataType}
        assert types == {"BOOLEAN", "INTEGER", "FLOAT", "STRING", "JSON"}

    def test_data_quality_enum(self):
        """DataQuality enum must have correct values."""
        qualities = {q.value for q in DataQuality}
        assert qualities == {"GOOD", "BAD", "UNCERTAIN", "UNKNOWN"}


class TestAdapterRegistry:
    """Test AdapterRegistry."""

    @pytest.mark.asyncio
    async def test_register_and_get(self):
        registry = AdapterRegistry()
        adapter_id = uuid4()
        tenant_id = uuid4()
        adapter = MockAdapter(adapter_id)

        await registry.register(adapter_id, tenant_id, adapter)
        result = await registry.get(adapter_id, tenant_id)
        assert result is adapter

    @pytest.mark.asyncio
    async def test_register_duplicate_raises(self):
        registry = AdapterRegistry()
        adapter_id = uuid4()
        tenant_id = uuid4()
        adapter = MockAdapter(adapter_id)

        await registry.register(adapter_id, tenant_id, adapter)
        with pytest.raises(AdapterAlreadyExistsError):
            await registry.register(adapter_id, tenant_id, adapter)

    @pytest.mark.asyncio
    async def test_unregister(self):
        registry = AdapterRegistry()
        adapter_id = uuid4()
        tenant_id = uuid4()
        adapter = MockAdapter(adapter_id)

        await registry.register(adapter_id, tenant_id, adapter)
        await registry.unregister(adapter_id, tenant_id)
        result = await registry.get(adapter_id, tenant_id)
        assert result is None

    @pytest.mark.asyncio
    async def test_unregister_not_found_raises(self):
        registry = AdapterRegistry()
        with pytest.raises(AdapterNotFoundError):
            await registry.unregister(uuid4(), uuid4())

    @pytest.mark.asyncio
    async def test_list_for_tenant(self):
        registry = AdapterRegistry()
        tenant_id = uuid4()
        adapter1 = MockAdapter(uuid4())
        adapter2 = MockAdapter(uuid4())

        await registry.register(uuid4(), tenant_id, adapter1)
        await registry.register(uuid4(), tenant_id, adapter2)
        adapters = await registry.list_for_tenant(tenant_id)
        assert len(adapters) == 2

    @pytest.mark.asyncio
    async def test_tenant_isolation(self):
        registry = AdapterRegistry()
        tenant_a = uuid4()
        tenant_b = uuid4()
        adapter = MockAdapter(uuid4())

        await registry.register(uuid4(), tenant_a, adapter)
        result = await registry.get(adapter.adapter_id, tenant_b)
        assert result is None

    @pytest.mark.asyncio
    async def test_clear_tenant(self):
        registry = AdapterRegistry()
        tenant_id = uuid4()
        adapter = MockAdapter(uuid4())

        await registry.register(uuid4(), tenant_id, adapter)
        count = await registry.clear_tenant(tenant_id)
        assert count == 1
        result = await registry.count_for_tenant(tenant_id)
        assert result == 0


class TestCircuitBreaker:
    """Test CircuitBreaker."""

    @pytest.mark.asyncio
    async def test_closed_state(self):
        cb = CircuitBreaker(max_failures=3, reset_timeout=1.0)
        assert cb.state == "closed"
        assert await cb.allow_request() is True

    @pytest.mark.asyncio
    async def test_opens_after_failures(self):
        cb = CircuitBreaker(max_failures=2, reset_timeout=1.0)
        await cb.record_failure()
        await cb.record_failure()
        assert cb.state == "open"
        assert await cb.allow_request() is False

    @pytest.mark.asyncio
    async def test_half_open_after_timeout(self):
        cb = CircuitBreaker(max_failures=1, reset_timeout=0.01)
        await cb.record_failure()
        assert cb.state == "open"
        await asyncio.sleep(0.02)
        assert cb.state == "half_open"
        assert await cb.allow_request() is True

    def test_closes_on_success_from_half_open(self):
        cb = CircuitBreaker(max_failures=1, reset_timeout=0.01)
        asyncio.run(cb.record_failure())
        import time
        time.sleep(0.05)
        # After timeout, state should be half_open
        assert cb.state == "half_open"
        # record_success is async, need to await it
        asyncio.run(cb.record_success())
        assert cb.state == "closed"

    def test_reopens_on_failure_from_half_open(self):
        cb = CircuitBreaker(max_failures=1, reset_timeout=0.01)
        asyncio.run(cb.record_failure())
        import time
        time.sleep(0.05)
        assert cb.state == "half_open"
        asyncio.run(cb.record_failure())
        assert cb.state == "open"


class TestAdapterRuntime:
    """Test AdapterRuntime."""

    @pytest.mark.asyncio
    async def test_connect_success(self):
        runtime = AdapterRuntime(max_retries=2)
        adapter = MockAdapter(uuid4())
        await runtime.connect_with_retry(
            adapter, "test_endpoint", "cred_ref", {}
        )
        assert adapter._connected is True

    @pytest.mark.asyncio
    async def test_connect_failure_raises(self):
        runtime = AdapterRuntime(max_retries=1)

        class FailingAdapter(ProtocolAdapter):
            async def connect(self, endpoint, credentials_ref, config):
                raise ConnectionError("Connection refused")
            async def disconnect(self): pass
            async def health(self): return False
            async def discover(self): return []
            async def read(self, external_ids): return []
            async def write(self, external_id, value, data_type): return False
            async def subscribe(self, external_id, callback): return ""
            async def unsubscribe(self, subscription_id): pass
            def capabilities(self): return set()

        adapter = FailingAdapter()
        with pytest.raises(AdapterConnectionError):
            await runtime.connect_with_retry(adapter, "bad_endpoint", "cred", {})

    @pytest.mark.asyncio
    async def test_health_check(self):
        runtime = AdapterRuntime()
        adapter = MockAdapter(uuid4())
        await adapter.connect("endpoint", "cred", {})
        healthy = await runtime.check_health(adapter)
        assert healthy is True

    @pytest.mark.asyncio
    async def test_disconnect_cleanup(self):
        runtime = AdapterRuntime()
        adapter = MockAdapter(uuid4())
        await adapter.connect("endpoint", "cred", {})
        await runtime.disconnect_with_cleanup(adapter)
        assert adapter._connected is False


class TestAdapterHealthChecker:
    """Test AdapterHealthChecker."""

    @pytest.mark.asyncio
    async def test_health_check_success(self):
        checker = AdapterHealthChecker()
        adapter = MockAdapter(uuid4())
        await adapter.connect("endpoint", "cred", {})

        status = await checker.check(
            adapter_id=adapter.adapter_id,
            tenant_id=uuid4(),
            adapter=adapter,
            adapter_type="mock",
            endpoint="endpoint",
            circuit_state="closed",
        )
        assert status.connected is True
        assert status.error_message is None

    @pytest.mark.asyncio
    async def test_health_check_failure(self):
        checker = AdapterHealthChecker()
        adapter = MockAdapter(uuid4())

        status = await checker.check(
            adapter_id=adapter.adapter_id,
            tenant_id=uuid4(),
            adapter=adapter,
            adapter_type="mock",
            endpoint="endpoint",
            circuit_state="closed",
        )
        assert status.connected is False

    def test_get_status(self):
        checker = AdapterHealthChecker()
        adapter_id = uuid4()
        tenant_id = uuid4()
        status = AdapterHealthStatus(
            adapter_id=adapter_id, tenant_id=tenant_id,
            adapter_type="mock", endpoint="ep",
            connected=True, circuit_state="closed",
        )
        checker._statuses[(adapter_id, tenant_id)] = status
        result = checker.get_status(adapter_id, tenant_id)
        assert result is status


class TestCapabilityAdapterMatcher:
    """Test CapabilityAdapterMatcher (ADR-008)."""

    @pytest.mark.asyncio
    async def test_match_temperature_capability(self):
        matcher = CapabilityAdapterMatcher()
        matches = await matcher.match(
            capability_key="temperature",
            data_type="FLOAT",
        )
        assert len(matches) > 0
        # BACnet should be top candidate for temperature
        assert matches[0].adapter_type in ("bacnet", "modbus", "opcua")
        assert matches[0].confidence > 0

    @pytest.mark.asyncio
    async def test_match_power_capability(self):
        matcher = CapabilityAdapterMatcher()
        matches = await matcher.match(
            capability_key="power",
            data_type="FLOAT",
        )
        assert len(matches) > 0
        # Modbus and OPC-UA should match for power
        types = {m.adapter_type for m in matches}
        assert "modbus" in types or "opcua" in types

    @pytest.mark.asyncio
    async def test_match_alarm_capability(self):
        matcher = CapabilityAdapterMatcher()
        matches = await matcher.match(
            capability_key="alarm",
            data_type="BOOLEAN",
        )
        assert len(matches) > 0
        # Multiple adapters should support alarm
        types = {m.adapter_type for m in matches}
        assert len(types) >= 2

    @pytest.mark.asyncio
    async def test_match_returns_sorted_by_confidence(self):
        matcher = CapabilityAdapterMatcher()
        matches = await matcher.match(
            capability_key="temperature_measurement",
            data_type="FLOAT",
        )
        for i in range(len(matches) - 1):
            assert matches[i].confidence >= matches[i + 1].confidence

    @pytest.mark.asyncio
    async def test_validate_adapter_supports_capability(self):
        matcher = CapabilityAdapterMatcher()
        result = await matcher.validate_adapter_supports_capability(
            adapter_type="bacnet",
            capability_key="temperature",
            required_capabilities=["READ", "SUBSCRIBE"],
        )
        assert result is True

    @pytest.mark.asyncio
    async def test_match_no_candidates_for_unknown_capability(self):
        matcher = CapabilityAdapterMatcher()
        matches = await matcher.match(
            capability_key="unknown_xyz_123",
            data_type="FLOAT",
        )
        # Should return empty or very low confidence
        assert all(m.confidence < 0.1 for m in matches) if matches else True


class TestAdapterModels:
    """Test adapter data models."""

    def test_adapter_config_valid(self):
        config = AdapterConfig(
            adapter_type="bacnet",
            endpoint="192.168.1.100:47808",
            credentials_ref="bacnet_cred_001",
            config={"network_range": "192.168.1.0/24"},
        )
        assert config.adapter_type == "bacnet"
        assert config.endpoint == "192.168.1.100:47808"

    def test_device_mapping_valid(self):
        mapping = DeviceMapping(
            datapoint_key="temperature",
            protocol_address="analogInput:1:presentValue",
            protocol_config={"object_type": "analogInput", "object_instance": 1},
            direction="read",
        )
        assert mapping.datapoint_key == "temperature"
        assert mapping.direction == "read"

    def test_capability_match_valid(self):
        match = CapabilityMatch(
            adapter_type="bacnet",
            confidence=0.95,
            required_capabilities=["READ", "SUBSCRIBE"],
        )
        assert match.confidence == 0.95
        assert "READ" in match.required_capabilities


class TestAdapterExceptions:
    """Test adapter exception classes."""

    def test_adapter_error(self):
        exc = AdapterError("test error", "TEST_CODE")
        assert exc.code == "TEST_CODE"
        assert exc.message == "test error"

    def test_adapter_connection_error(self):
        exc = AdapterConnectionError("192.168.1.1:502", "timeout")
        assert "192.168.1.1:502" in exc.message
        assert exc.code == "ADAPTER_CONNECTION_ERROR"

    def test_adapter_protocol_error(self):
        from services.adapter.exceptions import AdapterProtocolError
        exc = AdapterProtocolError("bacnet", "read", "invalid object")
        assert "bacnet" in exc.message
        assert exc.code == "ADAPTER_PROTOCOL_ERROR"

    def test_adapter_not_found_error(self):
        exc = AdapterNotFoundError("bacnet", uuid4())
        assert "bacnet" in exc.message
        assert exc.code == "ADAPTER_NOT_FOUND"

    def test_adapter_already_exists_error(self):
        exc = AdapterAlreadyExistsError(uuid4(), uuid4())
        assert exc.code == "ADAPTER_ALREADY_EXISTS"

    def test_adapter_not_connected_error(self):
        exc = AdapterNotConnectedError(uuid4())
        assert exc.code == "ADAPTER_NOT_CONNECTED"

    def test_adapter_capability_mismatch_error(self):
        exc = AdapterCapabilityMismatchError("modbus", "DISCOVERY")
        assert "modbus" in exc.message
        assert exc.code == "ADAPTER_CAPABILITY_MISMATCH"
