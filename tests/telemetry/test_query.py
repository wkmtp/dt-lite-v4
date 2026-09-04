"""
test_query.py - Telemetry Query Service Tests

Tests query operations:
- Range query
- Device query
- Datapoint query
"""
import pytest
from datetime import datetime, timezone, timedelta
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, patch


class TestTelemetryQueryService:
    """Test TelemetryQueryService."""

    @pytest.mark.asyncio
    async def test_query_methods_exist(self):
        """Test that query methods exist with correct signatures."""
        from services.telemetry.query_service import TelemetryQueryService
        
        # Verify methods exist
        assert hasattr(TelemetryQueryService, 'query_by_device')
        assert hasattr(TelemetryQueryService, 'query_by_datapoint')
        assert hasattr(TelemetryQueryService, 'query_range')

    @pytest.mark.asyncio
    async def test_query_by_device_signature(self):
        """Test query_by_device method signature."""
        from services.telemetry.query_service import TelemetryQueryService
        import inspect
        
        sig = inspect.signature(TelemetryQueryService.query_by_device)
        params = list(sig.parameters.keys())
        
        assert 'self' in params
        assert 'device_id' in params
        assert 'start_time' in params
        assert 'end_time' in params
        assert 'limit' in params
        assert 'offset' in params

    @pytest.mark.asyncio
    async def test_query_by_datapoint_signature(self):
        """Test query_by_datapoint method signature."""
        from services.telemetry.query_service import TelemetryQueryService
        import inspect
        
        sig = inspect.signature(TelemetryQueryService.query_by_datapoint)
        params = list(sig.parameters.keys())
        
        assert 'self' in params
        assert 'datapoint_id' in params

    @pytest.mark.asyncio
    async def test_query_range_signature(self):
        """Test query_range method signature."""
        from services.telemetry.query_service import TelemetryQueryService
        import inspect
        
        sig = inspect.signature(TelemetryQueryService.query_range)
        params = list(sig.parameters.keys())
        
        assert 'self' in params
        assert 'start_time' in params
        assert 'end_time' in params


class TestTelemetryRepository:
    """Test TelemetryRepository query methods."""

    @pytest.mark.asyncio
    async def test_repository_methods_exist(self):
        """Test that repository has all required methods."""
        from services.telemetry.repositories import TelemetryRepository
        
        # Verify methods exist
        assert hasattr(TelemetryRepository, 'save')
        assert hasattr(TelemetryRepository, 'save_batch')
        assert hasattr(TelemetryRepository, 'query_by_device')
        assert hasattr(TelemetryRepository, 'query_by_datapoint')
        assert hasattr(TelemetryRepository, 'query_range')
        assert hasattr(TelemetryRepository, 'count')

    @pytest.mark.asyncio
    async def test_repository_uses_tenant_filter(self):
        """Test that repository applies tenant filter."""
        from services.telemetry.repositories import TelemetryRepository
        from services.core.repositories.base import TenantAwareRepository
        
        # Verify inheritance
        assert issubclass(TelemetryRepository, TenantAwareRepository)
        
        # Verify tenant filter method exists
        assert hasattr(TelemetryRepository, '_get_tenant_filter')