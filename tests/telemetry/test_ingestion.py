"""
test_ingestion.py - Telemetry Ingestion Service Tests

Tests single and batch ingestion with validation:
- Timestamp validation
- Timezone conversion
- Data type validation
- Quality validation
- Batch atomicity
"""
import pytest
from datetime import datetime, timezone
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, patch

from services.iota.contracts import NormalizedTelemetry
from services.telemetry.services import TelemetryIngestionService
from services.telemetry.exceptions import (
    TelemetryValidationError,
    TelemetryDeviceNotFoundError,
    TelemetryTenantMismatchError,
)


@pytest.fixture
def sample_telemetry():
    """Create a valid NormalizedTelemetry object."""
    return NormalizedTelemetry(
        tenant_id=str(uuid4()),
        device_id=str(uuid4()),
        datapoint_id=str(uuid4()),
        event_time=datetime.now(timezone.utc),
        ingested_at=datetime.now(timezone.utc),
        value=25.5,
        data_type="FLOAT",
        unit="degC",
        quality="GOOD",
        metadata={},
    )


@pytest.fixture
def sample_device():
    """Create a mock device."""
    device = MagicMock()
    device.id = uuid4()
    device.tenant_id = uuid4()
    return device


@pytest.fixture
def sample_datapoint():
    """Create a mock datapoint."""
    datapoint = MagicMock()
    datapoint.id = uuid4()
    datapoint.tenant_id = uuid4()
    return datapoint


class TestIngestSingle:
    """Test single telemetry point ingestion."""

    @pytest.mark.asyncio
    async def test_ingest_single_success(self, sample_telemetry, sample_device, sample_datapoint):
        """Test successful single telemetry ingestion."""
        mock_session = AsyncMock()
        
        # Create mock objects for the services
        mock_telemetry_repo = MagicMock()
        mock_device_repo = MagicMock()
        mock_datapoint_repo = MagicMock()
        
        # Mock the repository methods
        mock_device_repo.get_by_id_for_tenant = AsyncMock(return_value=sample_device)
        mock_datapoint_repo.get_by_id_for_tenant = AsyncMock(return_value=sample_datapoint)
        mock_point = MagicMock()
        mock_point.id = uuid4()
        mock_telemetry_repo.save = AsyncMock(return_value=mock_point)
        
        # Create service with mocked repositories
        with patch('services.telemetry.services.TelemetryRepository', return_value=mock_telemetry_repo), \
             patch('services.telemetry.services.DeviceRepository', return_value=mock_device_repo), \
             patch('services.telemetry.services.DataPointRepository', return_value=mock_datapoint_repo):
            
            service = TelemetryIngestionService(mock_session)
            result = await service.ingest(sample_telemetry, sample_device.tenant_id)
            
            assert result is not None
            mock_device_repo.get_by_id_for_tenant.assert_called_once()
            mock_datapoint_repo.get_by_id_for_tenant.assert_called_once()
            mock_telemetry_repo.save.assert_called_once()

    @pytest.mark.asyncio
    async def test_ingest_single_invalid_data_type(self, sample_telemetry):
        """Test ingestion fails with invalid data type."""
        mock_session = AsyncMock()
        
        # Invalid data_type
        sample_telemetry.data_type = "INVALID_TYPE"
        
        with patch('services.telemetry.services.TelemetryRepository'), \
             patch('services.telemetry.services.DeviceRepository'), \
             patch('services.telemetry.services.DataPointRepository'):
            
            service = TelemetryIngestionService(mock_session)
            with pytest.raises(TelemetryValidationError):
                await service.ingest(sample_telemetry, sample_telemetry.tenant_id)

    @pytest.mark.asyncio
    async def test_ingest_single_invalid_quality(self, sample_telemetry):
        """Test ingestion fails with invalid quality."""
        mock_session = AsyncMock()
        
        # Invalid quality
        sample_telemetry.quality = "INVALID_QUALITY"
        
        with patch('services.telemetry.services.TelemetryRepository'), \
             patch('services.telemetry.services.DeviceRepository'), \
             patch('services.telemetry.services.DataPointRepository'):
            
            service = TelemetryIngestionService(mock_session)
            with pytest.raises(TelemetryValidationError):
                await service.ingest(sample_telemetry, sample_telemetry.tenant_id)

    @pytest.mark.asyncio
    async def test_ingest_single_missing_device(self, sample_telemetry):
        """Test ingestion fails when device not found."""
        mock_session = AsyncMock()
        
        mock_device_repo = MagicMock()
        mock_datapoint_repo = MagicMock()
        
        mock_device_repo.get_by_id_for_tenant = AsyncMock(return_value=None)
        mock_datapoint_repo.get_by_id_for_tenant = AsyncMock()
        
        with patch('services.telemetry.services.TelemetryRepository'), \
             patch('services.telemetry.services.DeviceRepository', return_value=mock_device_repo), \
             patch('services.telemetry.services.DataPointRepository', return_value=mock_datapoint_repo):
            
            service = TelemetryIngestionService(mock_session)
            with pytest.raises(TelemetryDeviceNotFoundError):
                await service.ingest(sample_telemetry, uuid4())

    @pytest.mark.asyncio
    async def test_ingest_single_missing_datapoint(self, sample_telemetry, sample_device):
        """Test ingestion fails when datapoint not found."""
        mock_session = AsyncMock()
        
        mock_device_repo = MagicMock()
        mock_datapoint_repo = MagicMock()
        
        mock_device_repo.get_by_id_for_tenant = AsyncMock(return_value=sample_device)
        mock_datapoint_repo.get_by_id_for_tenant = AsyncMock(return_value=None)
        
        with patch('services.telemetry.services.TelemetryRepository'), \
             patch('services.telemetry.services.DeviceRepository', return_value=mock_device_repo), \
             patch('services.telemetry.services.DataPointRepository', return_value=mock_datapoint_repo):
            
            service = TelemetryIngestionService(mock_session)
            with pytest.raises(TelemetryTenantMismatchError):
                await service.ingest(sample_telemetry, sample_device.tenant_id)


class TestIngestBatch:
    """Test batch telemetry ingestion."""

    @pytest.mark.asyncio
    async def test_ingest_batch_success(self, sample_device, sample_datapoint):
        """Test successful batch ingestion."""
        mock_session = AsyncMock()
        
        # Create multiple telemetry points
        telemetries = [
            NormalizedTelemetry(
                tenant_id=str(sample_device.tenant_id),
                device_id=str(sample_device.id),
                datapoint_id=str(sample_datapoint.id),
                event_time=datetime.now(timezone.utc),
                ingested_at=datetime.now(timezone.utc),
                value=25.5,
                data_type="FLOAT",
                quality="GOOD",
                metadata={},
            )
            for _ in range(5)
        ]
        
        mock_telemetry_repo = MagicMock()
        mock_device_repo = MagicMock()
        mock_datapoint_repo = MagicMock()
        
        mock_device_repo.get_by_id_for_tenant = AsyncMock(return_value=sample_device)
        mock_datapoint_repo.get_by_id_for_tenant = AsyncMock(return_value=sample_datapoint)
        mock_telemetry_repo.save_batch = AsyncMock(return_value=5)
        
        with patch('services.telemetry.services.TelemetryRepository', return_value=mock_telemetry_repo), \
             patch('services.telemetry.services.DeviceRepository', return_value=mock_device_repo), \
             patch('services.telemetry.services.DataPointRepository', return_value=mock_datapoint_repo):
            
            service = TelemetryIngestionService(mock_session)
            count = await service.ingest_batch(telemetries, sample_device.tenant_id)
            
            assert count == 5
            mock_device_repo.get_by_id_for_tenant.assert_called_once()
            mock_datapoint_repo.get_by_id_for_tenant.assert_called_once()
            mock_telemetry_repo.save_batch.assert_called_once()

    @pytest.mark.asyncio
    async def test_ingest_batch_empty_list(self):
        """Test batch ingestion with empty list."""
        mock_session = AsyncMock()
        
        with patch('services.telemetry.services.TelemetryRepository'), \
             patch('services.telemetry.services.DeviceRepository'), \
             patch('services.telemetry.services.DataPointRepository'):
            
            service = TelemetryIngestionService(mock_session)
            count = await service.ingest_batch([], uuid4())
            
            assert count == 0

    @pytest.mark.asyncio
    async def test_ingest_batch_invalid_point_fails_all(self, sample_device, sample_datapoint):
        """Test batch fails if any point is invalid."""
        mock_session = AsyncMock()
        
        telemetries = [
            NormalizedTelemetry(
                tenant_id=str(sample_device.tenant_id),
                device_id=str(sample_device.id),
                datapoint_id=str(sample_datapoint.id),
                event_time=datetime.now(timezone.utc),
                ingested_at=datetime.now(timezone.utc),
                value=25.5,
                data_type="FLOAT",
                quality="GOOD",
                metadata={},
            ),
            NormalizedTelemetry(
                tenant_id=str(sample_device.tenant_id),
                device_id=str(sample_device.id),
                datapoint_id=str(sample_datapoint.id),
                event_time=datetime.now(timezone.utc),
                ingested_at=datetime.now(timezone.utc),
                value=25.5,
                data_type="INVALID_TYPE",  # Invalid
                quality="GOOD",
                metadata={},
            ),
        ]
        
        mock_device_repo = MagicMock()
        mock_datapoint_repo = MagicMock()
        
        mock_device_repo.get_by_id_for_tenant = AsyncMock(return_value=sample_device)
        mock_datapoint_repo.get_by_id_for_tenant = AsyncMock(return_value=sample_datapoint)
        
        with patch('services.telemetry.services.TelemetryRepository'), \
             patch('services.telemetry.services.DeviceRepository', return_value=mock_device_repo), \
             patch('services.telemetry.services.DataPointRepository', return_value=mock_datapoint_repo):
            
            service = TelemetryIngestionService(mock_session)
            with pytest.raises(TelemetryValidationError):
                await service.ingest_batch(telemetries, sample_device.tenant_id)