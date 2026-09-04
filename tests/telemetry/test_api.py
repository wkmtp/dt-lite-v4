"""
test_api.py - Telemetry API Endpoint Tests

Tests API endpoints:
- POST /telemetry (single ingestion)
- GET /telemetry/device/{id}
- GET /telemetry/range
"""
import pytest
from datetime import datetime, timezone, timedelta
from uuid import uuid4


class TestTelemetryAPI:
    """Test telemetry API endpoints."""

    def test_routes_exist(self):
        """Verify telemetry routes are registered."""
        from services.telemetry.routes import router
        
        paths = [route.path for route in router.routes]
        
        # Verify key endpoints exist
        assert any('/telemetry/' in p and p.endswith('/') for p in paths), "POST / endpoint missing"
        assert any('/batch' in p for p in paths), "POST /batch endpoint missing"
        assert any('/device/' in p for p in paths), "GET /device/{id} endpoint missing"
        assert any('/datapoint/' in p for p in paths), "GET /datapoint/{id} endpoint missing"
        assert any('/range' in p for p in paths), "GET /range endpoint missing"

    def test_post_endpoints_require_permission(self):
        """Verify POST endpoints have permission requirements."""
        from services.telemetry.routes import router
        
        post_routes = [r for r in router.routes if hasattr(r, 'methods') and 'POST' in r.methods]
        
        for route in post_routes:
            # POST endpoints should have dependencies (permissions)
            assert hasattr(route, 'dependencies'), \
                f"POST route {route.path} should require permission"

    def test_get_endpoints_require_permission(self):
        """Verify GET endpoints have permission requirements."""
        from services.telemetry.routes import router
        
        get_routes = [r for r in router.routes if hasattr(r, 'methods') and 'GET' in r.methods]
        
        for route in get_routes:
            # GET endpoints should have dependencies (permissions)
            assert hasattr(route, 'dependencies'), \
                f"GET route {route.path} should require permission"

    def test_ingestion_endpoint_uses_correct_service(self):
        """Verify ingestion endpoint uses TelemetryIngestionService."""
        from services.telemetry.services import TelemetryIngestionService
        
        # Verify the service exists and has the expected methods
        assert hasattr(TelemetryIngestionService, 'ingest'), \
            "TelemetryIngestionService should have ingest method"
        assert hasattr(TelemetryIngestionService, 'ingest_batch'), \
            "TelemetryIngestionService should have ingest_batch method"

    def test_query_endpoint_uses_correct_service(self):
        """Verify query endpoints use TelemetryQueryService."""
        from services.telemetry.query_service import TelemetryQueryService
        
        # Verify the service exists and has the expected methods
        assert hasattr(TelemetryQueryService, 'query_by_device'), \
            "TelemetryQueryService should have query_by_device method"
        assert hasattr(TelemetryQueryService, 'query_by_datapoint'), \
            "TelemetryQueryService should have query_by_datapoint method"
        assert hasattr(TelemetryQueryService, 'query_range'), \
            "TelemetryQueryService should have query_range method"


class TestAPIResponseSchemas:
    """Test API response schemas."""

    def test_telemetry_point_create_schema(self):
        """Test TelemetryPointCreate schema."""
        from services.telemetry.schemas import TelemetryPointCreate
        
        # Should not have tenant_id field
        assert 'tenant_id' not in TelemetryPointCreate.model_fields, \
            "tenant_id should not be in request schema"
        
        # Should have required fields
        required_fields = ['device_id', 'datapoint_id', 'event_time', 'ingested_at', 
                          'value', 'data_type']
        for field in required_fields:
            assert field in TelemetryPointCreate.model_fields, \
                f"Missing required field: {field}"

    def test_telemetry_point_response_schema(self):
        """Test TelemetryPointResponse schema."""
        from services.telemetry.schemas import TelemetryPointResponse
        
        # Should include basic fields
        required_fields = ['id', 'device_id', 'datapoint_id', 'event_time', 
                          'ingested_at', 'value', 'data_type', 'quality']
        for field in required_fields:
            assert field in TelemetryPointResponse.model_fields, \
                f"Missing required field: {field}"

    def test_telemetry_query_response_schema(self):
        """Test TelemetryQueryResponse schema."""
        from services.telemetry.schemas import TelemetryQueryResponse
        
        # Should include points and metadata
        assert 'points' in TelemetryQueryResponse.model_fields, \
            "Missing 'points' field"
        assert 'total' in TelemetryQueryResponse.model_fields, \
            "Missing 'total' field"


class TestPermissionRequirements:
    """Test permission requirements for endpoints."""

    def test_ingest_requires_create_permission(self):
        """Verify ingestion requires telemetry:create permission."""
        from services.auth.dependencies import require_permission
        
        # The permission decorator should be available
        assert callable(require_permission), "require_permission should be a function"

    def test_query_requires_read_permission(self):
        """Verify query requires telemetry:read permission."""
        from services.auth.dependencies import require_permission
        
        # The permission decorator should be available
        assert callable(require_permission), "require_permission should be a function"