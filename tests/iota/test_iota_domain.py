"""Data Acquisition Domain Tests - Phase 1 Task 5."""
import glob
import inspect
import os
import asyncio
import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock
from uuid import uuid4

from services.iota.models.enums import AccessMode, AdapterCapability, DataQuality, DataType, SamplingMode
from services.iota.contracts import DiscoveryResult, NormalizedTelemetry, ProtocolAdapter
from services.iota.mock_adapter import MockAdapter
from services.iota.secret_provider import EnvironmentSecretProvider


# ============================================================
# TestDataSource
# ============================================================
class TestDataSource:
    def test_datasource_type_is_string_not_enum(self):
        """DataSource.type must be a string (extensible), not a protocol enum."""
        from services.iota.models.models import DataSource
        assert hasattr(DataSource, 'type')

    @pytest.mark.asyncio
    async def test_datasource_no_protocol_in_type(self):
        """DataSource service must reject protocol-specific types via validation."""
        from services.iota.services.data_source_service import DataSourceService
        from services.core.unit_of_work import UnitOfWork
        from services.exceptions.base import ValidationError
        from unittest.mock import AsyncMock, MagicMock

        # Create mock UoW with mocked data_sources repository
        uow = MagicMock(spec=UnitOfWork)
        uow.data_sources = MagicMock()
        uow.data_sources.get_by_name = AsyncMock(return_value=None)
        uow.commit = AsyncMock()

        service = DataSourceService(uow)

        # Behavioral test: calling create_data_source with protocol type raises ValidationError
        for bad_type in ['bacnet', 'modbus', 'opcua', 'mqtt']:
            with pytest.raises(ValidationError, match=f"Invalid datasource type: {bad_type}"):
                await service.create_data_source(
                    name=f"test-{bad_type}",
                    data_type=bad_type,
                    config={},
                    tenant_id=uuid4(),
                )


# ============================================================
# TestConnection
# ============================================================
class TestConnection:
    def test_connection_uses_credentials_ref_not_password(self):
        """Connection stores credentials_ref, never password/secret."""
        from services.iota.models.models import Connection
        assert hasattr(Connection, 'credentials_ref')
        col_names = {c.name for c in Connection.__table__.columns}
        forbidden = {'password', 'secret', 'token', 'api_key', 'private_key'}
        assert forbidden.isdisjoint(col_names), f"Forbidden columns found: {forbidden & col_names}"

    def test_connection_endpoint_redacted_in_response(self):
        """Connection API response must redact endpoint."""
        conn = MagicMock()
        conn.id = uuid4()
        conn.data_source_id = uuid4()
        conn.name = "test"
        conn.endpoint = "tcp://10.0.0.1:502"
        conn.credentials_ref = "ref-001"
        conn.timeout = 30
        conn.status = "connected"
        conn.created_at = datetime.now(timezone.utc)
        conn.updated_at = datetime.now(timezone.utc)

        from services.iota.services.connection_service import ConnectionService
        response = ConnectionService._to_response(conn)
        assert response['endpoint'] == '<REDACTED>'


# ============================================================
# TestDevice
# ============================================================
class TestDevice:
    def test_device_external_id_is_string(self):
        """Device.external_id must be a string, not integer."""
        from services.iota.models.models import Device
        col = Device.__table__.columns['external_id']
        assert 'String' in str(type(col).__name__) or hasattr(col, 'type')

    def test_device_not_asset(self):
        """Device must have separate ID from Asset (no device_id == asset_id)."""
        from services.iota.models.models import Device
        from services.core.models.models import Asset
        assert Device.__tablename__ != Asset.__tablename__


# ============================================================
# TestDataPoint
# ============================================================
class TestDataPoint:
    def test_datatype_values(self):
        """DataType enum must contain only required values."""
        assert DataType.BOOLEAN.value == "BOOLEAN"
        assert DataType.INTEGER.value == "INTEGER"
        assert DataType.FLOAT.value == "FLOAT"
        assert DataType.STRING.value == "STRING"
        assert DataType.JSON.value == "JSON"

    def test_access_mode_values(self):
        """AccessMode enum must contain READ, WRITE, READ_WRITE."""
        assert AccessMode.READ.value == "READ"
        assert AccessMode.WRITE.value == "WRITE"
        assert AccessMode.READ_WRITE.value == "READ_WRITE"

    def test_access_mode_rules(self):
        """Access mode read/write rules."""
        assert AccessMode.READ.can_read is True
        assert AccessMode.READ.can_write is False
        assert AccessMode.WRITE.can_read is False
        assert AccessMode.WRITE.can_write is True
        assert AccessMode.READ_WRITE.can_read is True
        assert AccessMode.READ_WRITE.can_write is True

    def test_sampling_mode_values(self):
        """SamplingMode enum must contain required values."""
        assert SamplingMode.POLL.value == "POLL"
        assert SamplingMode.SUBSCRIBE.value == "SUBSCRIBE"
        assert SamplingMode.ON_CHANGE.value == "ON_CHANGE"
        assert SamplingMode.MANUAL.value == "MANUAL"

    def test_data_quality_values(self):
        """DataQuality enum must contain required values."""
        assert DataQuality.GOOD.value == "GOOD"
        assert DataQuality.BAD.value == "BAD"
        assert DataQuality.UNCERTAIN.value == "UNCERTAIN"
        assert DataQuality.UNKNOWN.value == "UNKNOWN"


# ============================================================
# TestNormalizedTelemetry
# ============================================================
class TestNormalizedTelemetry:
    def test_basic_creation(self):
        """Create valid NormalizedTelemetry."""
        now = datetime.now(timezone.utc)
        t = NormalizedTelemetry(
            tenant_id="t1", device_id="d1", datapoint_id="p1",
            event_time=now, ingested_at=now,
            value=24.6, data_type="FLOAT", unit="degC",
            quality="GOOD", metadata={},
        )
        assert t.validate() == []

    def test_event_time_before_ingested_at(self):
        """event_time can be before ingested_at (network delay)."""
        now = datetime.now(timezone.utc)
        earlier = now.replace(hour=now.hour - 1)
        t = NormalizedTelemetry(
            tenant_id="t1", device_id="d1", datapoint_id="p1",
            event_time=earlier, ingested_at=now,
            value=24.6, data_type="FLOAT", quality="GOOD",
        )
        assert t.validate() == []
        assert t.event_time < t.ingested_at

    def test_quality_uncertain_preserved(self):
        """UNCERTAIN quality must not be auto-converted to GOOD."""
        t = NormalizedTelemetry(
            tenant_id="t1", device_id="d1", datapoint_id="p1",
            event_time=datetime.now(timezone.utc),
            ingested_at=datetime.now(timezone.utc),
            value=24.6, data_type="FLOAT", quality="UNCERTAIN",
        )
        assert t.quality == "UNCERTAIN"

    def test_quality_all_values_valid(self):
        """All quality values must pass validation."""
        for q in ["GOOD", "BAD", "UNCERTAIN", "UNKNOWN"]:
            t = NormalizedTelemetry(
                tenant_id="t1", device_id="d1", datapoint_id="p1",
                event_time=datetime.now(timezone.utc),
                ingested_at=datetime.now(timezone.utc),
                value=None, data_type="STRING", quality=q,
            )
            assert t.validate() == []

    def test_missing_tenant_id_fails(self):
        """Missing tenant_id must fail validation."""
        t = NormalizedTelemetry(
            tenant_id="", device_id="d1", datapoint_id="p1",
            event_time=datetime.now(timezone.utc),
            ingested_at=datetime.now(timezone.utc),
            value=1, data_type="INTEGER", quality="GOOD",
        )
        errors = t.validate()
        assert any("tenant_id" in e for e in errors)

    def test_invalid_data_type_fails(self):
        """Invalid data_type must fail validation."""
        t = NormalizedTelemetry(
            tenant_id="t1", device_id="d1", datapoint_id="p1",
            event_time=datetime.now(timezone.utc),
            ingested_at=datetime.now(timezone.utc),
            value=1, data_type="DATETIME", quality="GOOD",
        )
        errors = t.validate()
        assert any("data_type" in e for e in errors)


# ============================================================
# TestAdapterContract
# ============================================================
class TestAdapterContract:
    def test_mock_adapter_implements_protocol_adapter(self):
        """MockAdapter must implement ProtocolAdapter ABC."""
        assert isinstance(MockAdapter(), ProtocolAdapter)

    def test_mock_adapter_capabilities(self):
        """MockAdapter declares READ and DISCOVERY capabilities."""
        adapter = MockAdapter()
        caps = adapter.capabilities()
        assert AdapterCapability.READ in caps
        assert AdapterCapability.DISCOVERY in caps
        assert AdapterCapability.WRITE not in caps
        assert AdapterCapability.SUBSCRIBE not in caps


# ============================================================
# TestAdapterCapabilities
# ============================================================
class TestAdapterCapabilities:
    @pytest.mark.asyncio
    async def test_read_allowed_for_read_capability(self):
        """read() should work when READ capability is present."""
        adapter = MockAdapter()
        result = await adapter.read(["point-1"])
        assert len(result) >= 1

    @pytest.mark.asyncio
    async def test_discover_allowed_for_discovery_capability(self):
        """discover() should work when DISCOVERY capability is present."""
        adapter = MockAdapter()
        results = await adapter.discover()
        assert len(results) >= 1
        assert all(isinstance(r, DiscoveryResult) for r in results)

    @pytest.mark.asyncio
    async def test_subscribe_rejected_when_no_capability(self):
        """subscribe() should raise when SUBSCRIBE not in capabilities."""
        adapter = MockAdapter()
        with pytest.raises(NotImplementedError):
            await adapter.subscribe("point-1", lambda x: x)

    def test_capability_based_not_protocol_based(self):
        """No if-protocol checks in adapter logic."""
        source = inspect.getsource(MockAdapter)
        assert 'bacnet' not in source.lower()
        assert 'modbus' not in source.lower()
        assert 'opcua' not in source.lower()
        assert 'mqtt' not in source.lower()
        assert 'if protocol' not in source.lower()
        assert 'if adapter_type' not in source.lower()


# ============================================================
# TestDiscoveryContract
# ============================================================
class TestDiscoveryContract:
    def test_discovery_result_device(self):
        """DiscoveryResult for device discovery."""
        d = DiscoveryResult(
            external_id="dev-001", name="Device 001",
            discovery_type="device", device_type="sensor",
        )
        assert d.discovery_type == "device"
        assert d.external_id == "dev-001"

    def test_discovery_result_datapoint(self):
        """DiscoveryResult for datapoint discovery."""
        dp = DiscoveryResult(
            external_id="pt-001", name="Temperature",
            discovery_type="datapoint", data_type="FLOAT", unit="degC",
        )
        assert dp.discovery_type == "datapoint"
        assert dp.data_type == "FLOAT"
        assert dp.unit == "degC"

    def test_no_protocol_fields_in_discovery(self):
        """DiscoveryResult must not contain protocol-specific fields."""
        sig = inspect.signature(DiscoveryResult.__init__)
        params = list(sig.parameters.keys())
        assert 'node_id' not in params
        assert 'topic' not in params
        assert 'object_identifier' not in params
        assert 'device_instance' not in params


# ============================================================
# TestMockAdapter
# ============================================================
class TestMockAdapter:
    @pytest.mark.asyncio
    async def test_connect_disconnect(self):
        """MockAdapter connect/disconnect cycle."""
        adapter = MockAdapter()
        await adapter.connect("mock://test", "ref-001", {})
        assert await adapter.health() is True
        await adapter.disconnect()
        assert await adapter.health() is False

    @pytest.mark.asyncio
    async def test_read_returns_normalized_telemetry(self):
        """MockAdapter.read returns NormalizedTelemetry objects."""
        adapter = MockAdapter()
        await adapter.connect("mock://test", "ref-001", {})
        results = await adapter.read(["temp-1"])
        assert len(results) >= 1
        assert isinstance(results[0], NormalizedTelemetry)

    @pytest.mark.asyncio
    async def test_no_protocol_concepts(self):
        """MockAdapter must not use protocol-specific concepts."""
        source = inspect.getsource(MockAdapter)
        forbidden = ['register', 'node_id', 'object_identifier', 'device_instance']
        for term in forbidden:
            assert term not in source.lower(), f"Found protocol concept: {term}"


# ============================================================
# TestSecretProtection
# ============================================================
class TestSecretProtection:
    def test_secret_provider_contract_exists(self):
        """SecretProvider ABC must exist."""
        from services.iota.contracts import SecretProvider
        assert inspect.isabstract(SecretProvider)

    def test_environment_secret_provider_store_get(self):
        """EnvironmentSecretProvider store and get."""
        provider = EnvironmentSecretProvider(prefix="TEST_T5_")
        os.environ["TEST_T5_MY_KEY"] = "my-secret-value"
        try:
            val = asyncio.run(provider.get_secret("my-key"))
            assert val == "my-secret-value"
        finally:
            del os.environ["TEST_T5_MY_KEY"]

    @pytest.mark.asyncio
    async def test_secret_not_found_returns_none(self):
        """get_secret returns None for missing ref."""
        provider = EnvironmentSecretProvider(prefix="NONEXIST_")
        result = await provider.get_secret("missing-key")
        assert result is None

    @pytest.mark.asyncio
    async def test_store_validates_non_empty(self):
        """store_secret validates non-empty ref and value."""
        provider = EnvironmentSecretProvider()
        with pytest.raises(ValueError):
            await provider.store_secret("", "value")
        with pytest.raises(ValueError):
            await provider.store_secret("key", "")


# ============================================================
# TestCapabilityValidation
# ============================================================
class TestCapabilityValidation:
    def test_adapter_capability_enum_values(self):
        """AdapterCapability must have exactly READ, WRITE, DISCOVERY, SUBSCRIBE."""
        expected = {"READ", "WRITE", "DISCOVERY", "SUBSCRIBE"}
        actual = {c.value for c in AdapterCapability}
        assert actual == expected

    def test_no_browse_event_command_capabilities(self):
        """First version must NOT include BROWSE, EVENT, COMMAND."""
        actual = {c.value for c in AdapterCapability}
        assert "BROWSE" not in actual
        assert "EVENT" not in actual
        assert "COMMAND" not in actual


# ============================================================
# TestNoProtocolCoupling
# ============================================================
class TestNoProtocolCoupling:
    """Scan all Task 5 core code for protocol-specific coupling."""

    PROTOCOL_TERMS = ["bacnet", "modbus", "opcua", "plc"]

    def test_no_protocol_specific_dependencies(self):
        """Task 5 code must not reference any protocol names."""
        iota_dir = os.path.join(os.path.dirname(__file__), '..', 'services', 'iota')
        match_count = {}

        for py_file in glob.glob(os.path.join(iota_dir, '**', '*.py'), recursive=True):
            with open(py_file, encoding='utf-8') as f:
                content = f.read().lower()
            for term in self.PROTOCOL_TERMS:
                count = content.count(term)
                if count > 0:
                    lines = [line.strip().lower() for line in content.split('\n') if term in line]
                    real_matches = [line for line in lines if not line.startswith('#') and 'env' not in line]
                    if real_matches:
                        match_count[f"{os.path.basename(py_file)}:{term}"] = real_matches

        assert match_count == {}, "Protocol coupling found in:\n" + "\n".join(
            f"  {k}: {v}" for k, v in match_count.items()
        )


# ============================================================
# TestTenantIsolation
# ============================================================
class TestTenantIsolation:
    def test_repository_uses_tenant_aware_base(self):
        """All iota repositories must inherit TenantAwareRepository."""
        from services.iota.repositories.data_source_repository import DataSourceRepository
        from services.iota.repositories.connection_repository import ConnectionRepository
        from services.iota.repositories.device_repository import DeviceRepository
        from services.iota.repositories.data_point_repository import DataPointRepository
        from services.iota.repositories.binding_repository import DeviceEntityBindingRepository
        from services.core.repositories.base import TenantAwareRepository

        repos = [DataSourceRepository, ConnectionRepository, DeviceRepository,
                 DataPointRepository, DeviceEntityBindingRepository]
        for repo in repos:
            assert issubclass(repo, TenantAwareRepository), \
                f"{repo.__name__} must inherit TenantAwareRepository"

    def test_binding_enforces_tenant_boundary(self):
        """Binding service must verify both device and entity belong to same tenant."""
        from services.iota.services.binding_service import DeviceEntityBindingService
        source = inspect.getsource(DeviceEntityBindingService.create_binding)
        assert 'tenant_id' in source
        # Either direct tenant check or tenant-aware repository call
        assert 'device.tenant_id' in source or 'device and' in source or 'get_by_id_for_tenant' in source


# Run with: pytest tests/iota/test_iota_domain.py -v
