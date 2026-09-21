"""
test_security.py - Telemetry Security Tests

Tests tenant isolation, cross-tenant rejection, and boundary enforcement:
- Cross-tenant device access blocked
- Cross-tenant datapoint access blocked
- Tenant filter required in queries
- No adapter dependency
- No protocol coupling
"""
import pytest
from datetime import datetime, timezone
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, patch

from services.telemetry.services import TelemetryIngestionService
from services.telemetry.exceptions import TelemetryDeviceNotFoundError, TelemetryTenantMismatchError
from services.iota.contracts import NormalizedTelemetry


class TestCrossTenantAccess:
    """Test cross-tenant access is blocked."""

    @pytest.mark.asyncio
    async def test_cross_tenant_device_rejected(self):
        """Test that accessing another tenant's device is rejected."""
        mock_session = AsyncMock()

        with patch('services.telemetry.services.DeviceRepository') as MockDeviceRepo:
            mock_device_repo = AsyncMock()
            MockDeviceRepo.return_value = mock_device_repo
            mock_device_repo.get_by_id_for_tenant = AsyncMock(return_value=None)

            service = TelemetryIngestionService(mock_session)
            service._device_repo = mock_device_repo

            telemetry = NormalizedTelemetry(
                tenant_id=str(uuid4()),
                device_id=str(uuid4()),
                datapoint_id=str(uuid4()),
                event_time=datetime.now(timezone.utc),
                ingested_at=datetime.now(timezone.utc),
                value=25.5,
                data_type="FLOAT",
                quality="GOOD",
                metadata={},
            )

            with pytest.raises(TelemetryDeviceNotFoundError):
                await service.ingest(telemetry, uuid4())

    @pytest.mark.asyncio
    async def test_cross_tenant_datapoint_rejected(self):
        """Test that accessing another tenant's datapoint is rejected."""
        mock_session = AsyncMock()

        with patch('services.telemetry.services.DeviceRepository') as MockDeviceRepo, \
             patch('services.telemetry.services.DataPointRepository') as MockDataPointRepo:

            mock_device_repo = AsyncMock()
            mock_datapoint_repo = AsyncMock()

            MockDeviceRepo.return_value = mock_device_repo
            MockDataPointRepo.return_value = mock_datapoint_repo

            mock_device_repo.get_by_id_for_tenant = AsyncMock(return_value=MagicMock())
            mock_datapoint_repo.get_by_id_for_tenant = AsyncMock(return_value=None)

            service = TelemetryIngestionService(mock_session)
            service._device_repo = mock_device_repo
            service._datapoint_repo = mock_datapoint_repo

            telemetry = NormalizedTelemetry(
                tenant_id=str(uuid4()),
                device_id=str(uuid4()),
                datapoint_id=str(uuid4()),
                event_time=datetime.now(timezone.utc),
                ingested_at=datetime.now(timezone.utc),
                value=25.5,
                data_type="FLOAT",
                quality="GOOD",
                metadata={},
            )

            with pytest.raises(TelemetryTenantMismatchError):
                await service.ingest(telemetry, uuid4())


class TestNoAdapterDependency:
    """Test no adapter dependency."""

    def test_no_adapter_imports_in_service(self):
        """Verify telemetry service doesn't import from adapter."""
        import services.telemetry.services as telemetry_services
        source = telemetry_services.__file__

        with open(source, 'r', encoding='utf-8') as f:
            content = f.read()

        assert 'from services.adapter' not in content
        assert 'import services.adapter' not in content

    def test_no_protocol_names_in_code(self):
        """Verify no protocol names appear in code."""
        import services.telemetry.services as telemetry_services

        with open(telemetry_services.__file__, 'r', encoding='utf-8') as f:
            content = f.read()

        # Check that protocol names don't appear in executable code
        protocol_names = ['bacnet', 'modbus', 'opcua', 'mqtt', 'plc']
        for name in protocol_names:
            # Count occurrences - should be 0 in non-comment lines
            lines = [l.strip() for l in content.split('\n') if l.strip() and not l.strip().startswith('#')]
            for line in lines:
                assert name.lower() not in line.lower(), f"Protocol '{name}' found in service code"


class TestTenantIsolation:
    """Test tenant isolation is maintained."""

    def test_tenant_id_not_in_schema(self):
        """Verify tenant_id is not exposed in request schemas."""
        from services.telemetry.schemas import TelemetryPointCreate

        # Check using model_fields (Pydantic V2)
        assert 'tenant_id' not in TelemetryPointCreate.model_fields, \
            "tenant_id should not be in request schema"

    def test_query_response_no_tenant_info(self):
        """Verify query responses don't expose tenant information."""
        from services.telemetry.schemas import TelemetryQueryResponse

        # Check using model_fields (Pydantic V2)
        assert 'tenant_id' not in TelemetryQueryResponse.model_fields, \
            "tenant_id should not be in response schema"


class TestTenantFilterRequired:
    """Test tenant filter is required in queries."""

    def test_repository_uses_tenant_filter(self):
        """Verify repository applies tenant filter."""
        from services.telemetry.repositories import TelemetryRepository
        from services.core.repositories.base import TenantAwareRepository

        # Verify inheritance
        assert issubclass(TelemetryRepository, TenantAwareRepository)

        # Verify tenant filter method exists
        assert hasattr(TelemetryRepository, '_get_tenant_filter')
