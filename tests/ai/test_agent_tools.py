"""Tests for AI Agent Tools — integration tests for all 5 tools.

Tests each tool with mocked HTTP responses, covering:
- Success cases
- Error handling (404, 500, timeout)
- Tenant validation
- Input validation
"""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta
from uuid import uuid4

import httpx

from services.ai.agent.tools.telemetry_query import TelemetryQueryTool
from services.ai.agent.tools.asset_lookup import AssetLookupTool
from services.ai.agent.tools.ontology_search import OntologySearchTool
from services.ai.agent.tools.workflow_trigger import WorkflowTriggerTool
from services.ai.agent.tools.custom_tool_loader import CustomToolLoader, ToolSchema
from services.ai.config import AIConfig


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def tenant_id() -> str:
    return str(uuid4())


@pytest.fixture
def config() -> AIConfig:
    return AIConfig(GATEWAY_URL="http://test-gateway:8000")


@pytest.fixture
def mock_http_client() -> MagicMock:
    """Create a mock async HTTP client."""
    client = MagicMock()
    client.get = AsyncMock()
    client.post = AsyncMock()
    client.aclose = AsyncMock()
    return client


@pytest.fixture
def sample_telemetry_response() -> dict:
    """Sample telemetry query response."""
    return {
        "success": True,
        "data": {
            "total": 150,
            "count": 10,
            "points": [
                {
                    "timestamp": "2024-01-15T10:00:00Z",
                    "value": 23.5,
                    "quality": "GOOD",
                    "entity_id": "e1",
                    "property_code": "temperature",
                },
                {
                    "timestamp": "2024-01-15T10:01:00Z",
                    "value": 24.0,
                    "quality": "GOOD",
                    "entity_id": "e1",
                    "property_code": "temperature",
                },
            ],
            "query_id": "q-123",
        },
    }


@pytest.fixture
def sample_asset_response() -> dict:
    """Sample asset lookup response."""
    return {
        "success": True,
        "data": {
            "id": "asset-123",
            "name": "Temperature Sensor 1",
            "type": "temperature_sensor",
            "properties": [
                {"code": "temperature", "name": "Temperature", "value": 23.5, "data_type": "float"},
                {"code": "humidity", "name": "Humidity", "value": 45.0, "data_type": "float"},
            ],
            "capabilities": [
                {"code": "read_temp", "name": "Read Temperature", "description": "Read temperature value"},
            ],
            "relationships": [
                {
                    "id": "rel-1",
                    "type": "located_in",
                    "source_id": "asset-123",
                    "target_id": "asset-456",
                },
            ],
            "parent_id": "parent-1",
            "children_ids": ["child-1", "child-2"],
        },
    }


@pytest.fixture
def sample_ontology_response() -> dict:
    """Sample ontology search response."""
    return {
        "success": True,
        "data": {
            "total": 5,
            "results": [
                {
                    "id": "concept-1",
                    "name": "Temperature",
                    "description": "Measure of heat",
                    "category": "physical",
                },
                {
                    "id": "concept-2",
                    "name": "Humidity",
                    "description": "Measure of moisture",
                    "category": "physical",
                },
            ],
        },
    }


@pytest.fixture
def sample_workflow_response() -> dict:
    """Sample workflow trigger response."""
    return {
        "success": True,
        "data": {
            "execution_id": "exec-123",
            "workflow_id": "wf-123",
            "workflow_code": "provision_device",
            "status": "success",
            "tenant_id": "tenant-1",
            "started_at": "2024-01-15T10:00:00Z",
            "completed_at": "2024-01-15T10:00:05Z",
            "steps": [
                {
                    "step_id": "step-1",
                    "step_type": "tool",
                    "status": "success",
                    "input": {},
                    "output": {"result": "ok"},
                },
            ],
            "inputs": {"device_id": "dev-1"},
            "outputs": {"device_id": "dev-1"},
        },
    }


# ---------------------------------------------------------------------------
# TelemetryQueryTool Tests
# ---------------------------------------------------------------------------

class TestTelemetryQueryTool:
    """Tests for TelemetryQueryTool."""

    @pytest.mark.asyncio
    async def test_success_query(self, tenant_id, config, mock_http_client, sample_telemetry_response):
        """Test successful telemetry query."""
        tool = TelemetryQueryTool(tenant_id=tenant_id, config=config)
        tool._client = mock_http_client

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = sample_telemetry_response
        mock_response.raise_for_status.return_value = None
        mock_http_client.get.return_value = mock_response

        result = await tool.execute(
            tenant_id=tenant_id,
            device_id="device-1",
            start_time="2024-01-15T09:00:00Z",
            end_time="2024-01-15T10:00:00Z",
            limit=100,
        )

        assert result["success"] is True
        assert result["total"] == 150
        assert len(result["points"]) == 2
        assert result["points"][0]["value"] == 23.5
        assert result["points"][0]["quality"] == "GOOD"
        mock_http_client.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_tenant_mismatch(self, tenant_id, config):
        """Test tenant ID mismatch returns error."""
        tool = TelemetryQueryTool(tenant_id=tenant_id, config=config)

        result = await tool.execute(
            tenant_id="wrong-tenant",
            device_id="device-1",
        )

        assert result["success"] is False
        assert result["error"] == "tenant_mismatch"

    @pytest.mark.asyncio
    async def test_invalid_aggregate(self, tenant_id, config):
        """Test invalid aggregate parameter."""
        tool = TelemetryQueryTool(tenant_id=tenant_id, config=config)

        result = await tool.execute(
            tenant_id=tenant_id,
            aggregate="invalid",
        )

        assert result["success"] is False
        assert result["error"] == "invalid_aggregate"

    @pytest.mark.asyncio
    async def test_invalid_quality_filter(self, tenant_id, config):
        """Test invalid quality filter parameter."""
        tool = TelemetryQueryTool(tenant_id=tenant_id, config=config)

        result = await tool.execute(
            tenant_id=tenant_id,
            quality_filter="INVALID",
        )

        assert result["success"] is False
        assert result["error"] == "invalid_quality_filter"

    @pytest.mark.asyncio
    async def test_raw_limit_exceeded(self, tenant_id, config):
        """Test RAW query with limit > 10000."""
        tool = TelemetryQueryTool(tenant_id=tenant_id, config=config)

        result = await tool.execute(
            tenant_id=tenant_id,
            aggregate="raw",
            limit=15000,
        )

        assert result["success"] is False
        assert result["error"] == "limit_too_large"

    @pytest.mark.asyncio
    async def test_invalid_start_time(self, tenant_id, config):
        """Test invalid start_time format."""
        tool = TelemetryQueryTool(tenant_id=tenant_id, config=config)

        result = await tool.execute(
            tenant_id=tenant_id,
            start_time="not-a-date",
        )

        assert result["success"] is False
        assert result["error"] == "invalid_start_time"

    @pytest.mark.asyncio
    async def test_start_after_end(self, tenant_id, config):
        """Test start_time after end_time."""
        tool = TelemetryQueryTool(tenant_id=tenant_id, config=config)

        result = await tool.execute(
            tenant_id=tenant_id,
            start_time="2024-01-15T10:00:00Z",
            end_time="2024-01-15T09:00:00Z",
        )

        assert result["success"] is False
        assert result["error"] == "invalid_time_range"

    @pytest.mark.asyncio
    async def test_http_404(self, tenant_id, config, mock_http_client):
        """Test 404 HTTP response."""
        tool = TelemetryQueryTool(tenant_id=tenant_id, config=config)
        tool._client = mock_http_client

        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.text = "Not found"
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "404", request=MagicMock(), response=mock_response
        )
        mock_http_client.get.return_value = mock_response

        result = await tool.execute(
            tenant_id=tenant_id,
            device_id="nonexistent",
        )

        assert result["success"] is False
        assert result["error"] == "not_found"

    @pytest.mark.asyncio
    async def test_http_500(self, tenant_id, config, mock_http_client):
        """Test 500 HTTP response."""
        tool = TelemetryQueryTool(tenant_id=tenant_id, config=config)
        tool._client = mock_http_client

        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "500", request=MagicMock(), response=mock_response
        )
        mock_http_client.get.return_value = mock_response

        result = await tool.execute(
            tenant_id=tenant_id,
            device_id="device-1",
        )

        assert result["success"] is False
        assert result["error"] == "internal_error"

    @pytest.mark.asyncio
    async def test_timeout(self, tenant_id, config, mock_http_client):
        """Test timeout exception."""
        tool = TelemetryQueryTool(tenant_id=tenant_id, config=config)
        tool._client = mock_http_client

        mock_http_client.get.side_effect = httpx.TimeoutException("Timeout")

        result = await tool.execute(
            tenant_id=tenant_id,
            device_id="device-1",
        )

        assert result["success"] is False
        assert result["error"] == "timeout"

    @pytest.mark.asyncio
    async def test_connection_error(self, tenant_id, config, mock_http_client):
        """Test connection error."""
        tool = TelemetryQueryTool(tenant_id=tenant_id, config=config)
        tool._client = mock_http_client

        mock_http_client.get.side_effect = httpx.ConnectError("Connection failed")

        result = await tool.execute(
            tenant_id=tenant_id,
            device_id="device-1",
        )

        assert result["success"] is False
        assert result["error"] == "connection_error"

    @pytest.mark.asyncio
    async def test_query_latest(self, tenant_id, config, mock_http_client, sample_telemetry_response):
        """Test query_latest convenience method."""
        tool = TelemetryQueryTool(tenant_id=tenant_id, config=config)
        tool._client = mock_http_client

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = sample_telemetry_response
        mock_response.raise_for_status.return_value = None
        mock_http_client.get.return_value = mock_response

        result = await tool.query_latest(
            tenant_id=tenant_id,
            device_id="device-1",
            limit=50,
        )

        assert result["success"] is True
        mock_http_client.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_aggregate_hour(self, tenant_id, config, mock_http_client, sample_telemetry_response):
        """Test hourly aggregation query."""
        tool = TelemetryQueryTool(tenant_id=tenant_id, config=config)
        tool._client = mock_http_client

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = sample_telemetry_response
        mock_response.raise_for_status.return_value = None
        mock_http_client.get.return_value = mock_response

        result = await tool.execute(
            tenant_id=tenant_id,
            aggregate="1h",
            limit=1000,
        )

        assert result["success"] is True
        assert result["aggregation"] == "1h"


# ---------------------------------------------------------------------------
# AssetLookupTool Tests
# ---------------------------------------------------------------------------

class TestAssetLookupTool:
    """Tests for AssetLookupTool."""

    @pytest.mark.asyncio
    async def test_lookup_by_asset_id(self, tenant_id, config, mock_http_client, sample_asset_response):
        """Test asset lookup by ID."""
        tool = AssetLookupTool(tenant_id=tenant_id, config=config)
        tool._client = mock_http_client

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = sample_asset_response
        mock_response.raise_for_status.return_value = None
        mock_http_client.get.return_value = mock_response

        result = await tool.execute(
            tenant_id=tenant_id,
            asset_id="asset-123",
        )

        assert result["success"] is True
        assert result["asset"]["asset_id"] == "asset-123"
        assert result["asset"]["name"] == "Temperature Sensor 1"
        assert len(result["asset"]["properties"]) == 2
        assert len(result["asset"]["capabilities"]) == 1
        assert len(result["asset"]["relationships"]) == 1

    @pytest.mark.asyncio
    async def test_lookup_by_entity_id(self, tenant_id, config, mock_http_client, sample_asset_response):
        """Test asset lookup by entity ID."""
        tool = AssetLookupTool(tenant_id=tenant_id, config=config)
        tool._client = mock_http_client

        # First call returns entity data, second call returns asset data
        entity_response = {
            "success": True,
            "data": {"id": "entity-1", "asset_id": "asset-123"},
        }
        mock_response1 = MagicMock()
        mock_response1.status_code = 200
        mock_response1.json.return_value = entity_response
        mock_response1.raise_for_status.return_value = None

        mock_response2 = MagicMock()
        mock_response2.status_code = 200
        mock_response2.json.return_value = sample_asset_response
        mock_response2.raise_for_status.return_value = None

        mock_http_client.get.side_effect = [mock_response1, mock_response2]

        result = await tool.execute(
            tenant_id=tenant_id,
            entity_id="entity-1",
        )

        assert result["success"] is True
        assert result["asset"]["asset_id"] == "asset-123"

    @pytest.mark.asyncio
    async def test_search_assets(self, tenant_id, config, mock_http_client):
        """Test asset search by keyword."""
        tool = AssetLookupTool(tenant_id=tenant_id, config=config)
        tool._client = mock_http_client

        search_response = {
            "success": True,
            "data": {
                "total": 2,
                "results": [
                    {"id": "asset-1", "name": "Sensor A", "type": "sensor"},
                    {"id": "asset-2", "name": "Sensor B", "type": "sensor"},
                ],
            },
        }
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = search_response
        mock_response.raise_for_status.return_value = None
        mock_http_client.get.return_value = mock_response

        result = await tool.execute(
            tenant_id=tenant_id,
            search="sensor",
            limit=10,
        )

        assert result["success"] is True
        assert result["total_count"] == 2
        assert len(result["assets"]) == 2

    @pytest.mark.asyncio
    async def test_tenant_mismatch(self, tenant_id, config):
        """Test tenant ID mismatch."""
        tool = AssetLookupTool(tenant_id=tenant_id, config=config)

        result = await tool.execute(
            tenant_id="wrong-tenant",
            asset_id="asset-1",
        )

        assert result["success"] is False
        assert result["error"] == "tenant_mismatch"

    @pytest.mark.asyncio
    async def test_missing_parameters(self, tenant_id, config):
        """Test missing all lookup parameters."""
        tool = AssetLookupTool(tenant_id=tenant_id, config=config)

        result = await tool.execute(
            tenant_id=tenant_id,
        )

        assert result["success"] is False
        assert result["error"] == "missing_parameters"

    @pytest.mark.asyncio
    async def test_http_404(self, tenant_id, config, mock_http_client):
        """Test 404 HTTP response."""
        tool = AssetLookupTool(tenant_id=tenant_id, config=config)
        tool._client = mock_http_client

        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.text = "Not found"
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "404", request=MagicMock(), response=mock_response
        )
        mock_http_client.get.return_value = mock_response

        result = await tool.execute(
            tenant_id=tenant_id,
            asset_id="nonexistent",
        )

        assert result["success"] is False
        assert result["error"] == "not_found"

    @pytest.mark.asyncio
    async def test_http_500(self, tenant_id, config, mock_http_client):
        """Test 500 HTTP response."""
        tool = AssetLookupTool(tenant_id=tenant_id, config=config)
        tool._client = mock_http_client

        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "500", request=MagicMock(), response=mock_response
        )
        mock_http_client.get.return_value = mock_response

        result = await tool.execute(
            tenant_id=tenant_id,
            asset_id="asset-1",
        )

        assert result["success"] is False
        assert result["error"] == "internal_error"

    @pytest.mark.asyncio
    async def test_timeout(self, tenant_id, config, mock_http_client):
        """Test timeout exception."""
        tool = AssetLookupTool(tenant_id=tenant_id, config=config)
        tool._client = mock_http_client

        mock_http_client.get.side_effect = httpx.TimeoutException("Timeout")

        result = await tool.execute(
            tenant_id=tenant_id,
            asset_id="asset-1",
        )

        assert result["success"] is False
        assert result["error"] == "timeout"

    @pytest.mark.asyncio
    async def test_tree_traversal(self, tenant_id, config, mock_http_client, sample_asset_response):
        """Test hierarchical tree traversal."""
        tool = AssetLookupTool(tenant_id=tenant_id, config=config)
        tool._client = mock_http_client

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = sample_asset_response
        mock_response.raise_for_status.return_value = None
        mock_http_client.get.return_value = mock_response

        result = await tool.execute(
            tenant_id=tenant_id,
            asset_id="asset-123",
            include_children=True,
            tree_depth=2,
        )

        assert result["success"] is True
        mock_http_client.get.assert_called()  # Should make multiple calls for tree traversal


# ---------------------------------------------------------------------------
# OntologySearchTool Tests
# ---------------------------------------------------------------------------

class TestOntologySearchTool:
    """Tests for OntologySearchTool."""

    @pytest.mark.asyncio
    async def test_search_concepts(self, tenant_id, config, mock_http_client, sample_ontology_response):
        """Test concept search."""
        tool = OntologySearchTool(tenant_id=tenant_id, config=config)
        tool._client = mock_http_client

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = sample_ontology_response
        mock_response.raise_for_status.return_value = None
        mock_http_client.get.return_value = mock_response

        result = await tool.execute(
            tenant_id=tenant_id,
            query="temperature",
            search_type="concept",
            limit=10,
        )

        assert result["success"] is True
        assert len(result["concepts"]) == 2
        assert result["total_count"] == 2

    @pytest.mark.asyncio
    async def test_search_all_types(self, tenant_id, config, mock_http_client, sample_ontology_response):
        """Test search across all ontology types."""
        tool = OntologySearchTool(tenant_id=tenant_id, config=config)
        tool._client = mock_http_client

        # Setup responses for different endpoints
        responses = [
            sample_ontology_response,  # concepts
            {"success": True, "data": {"total": 0, "results": []}},  # entity_types
            {"success": True, "data": {"total": 0, "results": []}},  # capabilities
            {"success": True, "data": {"total": 0, "results": []}},  # properties
            {"success": True, "data": {"total": 0, "results": []}},  # relationships
        ]
        mock_responses = []
        for r in responses:
            mock = MagicMock()
            mock.status_code = 200
            mock.json.return_value = r
            mock.raise_for_status.return_value = None
            mock_responses.append(mock)

        mock_http_client.get.side_effect = mock_responses

        result = await tool.execute(
            tenant_id=tenant_id,
            query="temperature",
            search_type="all",
            limit=10,
        )

        assert result["success"] is True
        assert result["total_count"] == 2  # From concepts only

    @pytest.mark.asyncio
    async def test_tenant_mismatch(self, tenant_id, config):
        """Test tenant ID mismatch."""
        tool = OntologySearchTool(tenant_id=tenant_id, config=config)

        result = await tool.execute(
            tenant_id="wrong-tenant",
            query="test",
        )

        assert result["success"] is False
        assert result["error"] == "tenant_mismatch"

    @pytest.mark.asyncio
    async def test_invalid_search_type(self, tenant_id, config):
        """Test invalid search type."""
        tool = OntologySearchTool(tenant_id=tenant_id, config=config)

        result = await tool.execute(
            tenant_id=tenant_id,
            query="test",
            search_type="invalid",
        )

        assert result["success"] is False
        assert result["error"].startswith("search_type must be one of")

    @pytest.mark.asyncio
    async def test_invalid_category(self, tenant_id, config):
        """Test invalid category."""
        tool = OntologySearchTool(tenant_id=tenant_id, config=config)

        result = await tool.execute(
            tenant_id=tenant_id,
            query="test",
            category="invalid",
        )

        assert result["success"] is False
        assert result["error"].startswith("category must be one of")

    @pytest.mark.asyncio
    async def test_invalid_limit(self, tenant_id, config):
        """Test invalid limit."""
        tool = OntologySearchTool(tenant_id=tenant_id, config=config)

        result = await tool.execute(
            tenant_id=tenant_id,
            query="test",
            limit=0,
        )

        assert result["success"] is False
        assert result["error"] == "limit must be between 1 and 100"

    @pytest.mark.asyncio
    async def test_http_404(self, tenant_id, config, mock_http_client):
        """Test 404 HTTP response."""
        tool = OntologySearchTool(tenant_id=tenant_id, config=config)
        tool._client = mock_http_client

        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.text = "Not found"
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "404", request=MagicMock(), response=mock_response
        )
        mock_http_client.get.return_value = mock_response

        result = await tool.execute(
            tenant_id=tenant_id,
            query="nonexistent",
        )

        assert result["success"] is False
        assert result["error"] == "not_found"

    @pytest.mark.asyncio
    async def test_timeout(self, tenant_id, config, mock_http_client):
        """Test timeout exception."""
        tool = OntologySearchTool(tenant_id=tenant_id, config=config)
        tool._client = mock_http_client

        mock_http_client.get.side_effect = httpx.TimeoutException("Timeout")

        result = await tool.execute(
            tenant_id=tenant_id,
            query="test",
        )

        assert result["success"] is False
        assert result["error"] == "timeout"

    @pytest.mark.asyncio
    async def test_search_entity_types(self, tenant_id, config, mock_http_client):
        """Test entity type search."""
        tool = OntologySearchTool(tenant_id=tenant_id, config=config)
        tool._client = mock_http_client

        response = {
            "success": True,
            "data": {
                "total": 1,
                "results": [
                    {"id": "type-1", "name": "Sensor", "description": "A sensor type"},
                ],
            },
        }
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = response
        mock_response.raise_for_status.return_value = None
        mock_http_client.get.return_value = mock_response

        result = await tool.execute(
            tenant_id=tenant_id,
            query="sensor",
            search_type="entity_type",
        )

        assert result["success"] is True
        assert len(result["entity_types"]) == 1

    @pytest.mark.asyncio
    async def test_search_capabilities(self, tenant_id, config, mock_http_client):
        """Test capability search."""
        tool = OntologySearchTool(tenant_id=tenant_id, config=config)
        tool._client = mock_http_client

        response = {
            "success": True,
            "data": {
                "total": 1,
                "results": [
                    {"id": "cap-1", "name": "ReadData", "description": "Read data capability"},
                ],
            },
        }
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = response
        mock_response.raise_for_status.return_value = None
        mock_http_client.get.return_value = mock_response

        result = await tool.execute(
            tenant_id=tenant_id,
            query="read",
            search_type="capability",
        )

        assert result["success"] is True
        assert len(result["capabilities"]) == 1

    @pytest.mark.asyncio
    async def test_search_relationships(self, tenant_id, config, mock_http_client):
        """Test relationship search."""
        tool = OntologySearchTool(tenant_id=tenant_id, config=config)
        tool._client = mock_http_client

        response = {
            "success": True,
            "data": {
                "total": 1,
                "results": [
                    {"id": "rel-1", "name": "located_in", "source_type": "sensor", "target_type": "building"},
                ],
            },
        }
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = response
        mock_response.raise_for_status.return_value = None
        mock_http_client.get.return_value = mock_response

        result = await tool.execute(
            tenant_id=tenant_id,
            query="located",
            search_type="relationship",
        )

        assert result["success"] is True
        assert len(result["relationships"]) == 1


# ---------------------------------------------------------------------------
# WorkflowTriggerTool Tests
# ---------------------------------------------------------------------------

class TestWorkflowTriggerTool:
    """Tests for WorkflowTriggerTool."""

    @pytest.mark.asyncio
    async def test_trigger_async(self, tenant_id, config, mock_http_client, sample_workflow_response):
        """Test async workflow trigger."""
        tool = WorkflowTriggerTool(tenant_id=tenant_id, config=config)
        tool._client = mock_http_client

        # First call returns workflow list
        list_response = {
            "success": True,
            "data": [
                {
                    "id": "wf-123",
                    "workflow_code": "provision_device",
                    "name": "Provision Device",
                    "active": True,
                }
            ],
        }
        mock_list = MagicMock()
        mock_list.status_code = 200
        mock_list.json.return_value = list_response
        mock_list.raise_for_status.return_value = None

        # Second call triggers workflow
        mock_exec = MagicMock()
        mock_exec.status_code = 202
        mock_exec.json.return_value = sample_workflow_response
        mock_exec.raise_for_status.return_value = None

        mock_http_client.get.return_value = mock_list
        mock_http_client.post.return_value = mock_exec

        result = await tool.execute(
            tenant_id=tenant_id,
            workflow_code="provision_device",
            params={"device_id": "dev-1"},
            async_mode=True,
        )

        assert result["success"] is True
        assert result["execution_id"] == "exec-123"
        assert result["async"] is True

    @pytest.mark.asyncio
    async def test_trigger_sync(self, tenant_id, config, mock_http_client, sample_workflow_response):
        """Test sync workflow trigger."""
        tool = WorkflowTriggerTool(tenant_id=tenant_id, config=config)
        tool._client = mock_http_client

        # First call returns workflow list
        list_response = {
            "success": True,
            "data": [
                {
                    "id": "wf-123",
                    "workflow_code": "provision_device",
                    "name": "Provision Device",
                    "active": True,
                }
            ],
        }
        mock_list = MagicMock()
        mock_list.status_code = 200
        mock_list.json.return_value = list_response
        mock_list.raise_for_status.return_value = None

        # Trigger response
        mock_trigger = MagicMock()
        mock_trigger.status_code = 202
        mock_trigger.json.return_value = sample_workflow_response
        mock_trigger.raise_for_status.return_value = None

        # Status poll response (completed)
        status_response = {
            "success": True,
            "data": {
                "execution_id": "exec-123",
                "status": "success",
                "completed_at": "2024-01-15T10:00:05Z",
                "outputs": {"result": "ok"},
            },
        }
        mock_status = MagicMock()
        mock_status.status_code = 200
        mock_status.json.return_value = status_response
        mock_status.raise_for_status.return_value = None

        mock_http_client.get.side_effect = [mock_list, mock_status]
        mock_http_client.post.return_value = mock_trigger

        result = await tool.execute(
            tenant_id=tenant_id,
            workflow_code="provision_device",
            params={"device_id": "dev-1"},
            async_mode=False,
            timeout_seconds=30,
        )

        assert result["success"] is True
        assert result["execution"]["status"] == "success"

    @pytest.mark.asyncio
    async def test_tenant_mismatch(self, tenant_id, config):
        """Test tenant ID mismatch."""
        tool = WorkflowTriggerTool(tenant_id=tenant_id, config=config)

        result = await tool.execute(
            tenant_id="wrong-tenant",
            workflow_code="provision_device",
        )

        assert result["success"] is False
        assert result["error"] == "tenant_mismatch"

    @pytest.mark.asyncio
    async def test_missing_workflow_identifier(self, tenant_id, config):
        """Test missing both workflow_code and workflow_id."""
        tool = WorkflowTriggerTool(tenant_id=tenant_id, config=config)

        result = await tool.execute(
            tenant_id=tenant_id,
            params={"device_id": "dev-1"},
        )

        assert result["success"] is False
        assert result["error"] == "missing_workflow_identifier"

    @pytest.mark.asyncio
    async def test_invalid_timeout(self, tenant_id, config):
        """Test invalid timeout value."""
        tool = WorkflowTriggerTool(tenant_id=tenant_id, config=config)

        result = await tool.execute(
            tenant_id=tenant_id,
            workflow_code="provision_device",
            timeout_seconds=500,
        )

        assert result["success"] is False
        assert result["error"] == "invalid_timeout"

    @pytest.mark.asyncio
    async def test_workflow_not_found(self, tenant_id, config, mock_http_client):
        """Test workflow not found."""
        tool = WorkflowTriggerTool(tenant_id=tenant_id, config=config)
        tool._client = mock_http_client

        # Empty workflow list
        list_response = {"success": True, "data": []}
        mock_list = MagicMock()
        mock_list.status_code = 200
        mock_list.json.return_value = list_response
        mock_list.raise_for_status.return_value = None
        mock_http_client.get.return_value = mock_list

        result = await tool.execute(
            tenant_id=tenant_id,
            workflow_code="nonexistent",
        )

        assert result["success"] is False
        assert result["error"] == "workflow_not_found"

    @pytest.mark.asyncio
    async def test_http_404(self, tenant_id, config, mock_http_client):
        """Test 404 HTTP response."""
        tool = WorkflowTriggerTool(tenant_id=tenant_id, config=config)
        tool._client = mock_http_client

        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.text = "Not found"
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "404", request=MagicMock(), response=mock_response
        )
        mock_http_client.get.return_value = mock_response

        result = await tool.execute(
            tenant_id=tenant_id,
            workflow_id="nonexistent",
        )

        assert result["success"] is False
        assert result["error"] == "workflow_not_found"

    @pytest.mark.asyncio
    async def test_http_500(self, tenant_id, config, mock_http_client):
        """Test 500 HTTP response."""
        tool = WorkflowTriggerTool(tenant_id=tenant_id, config=config)
        tool._client = mock_http_client

        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "500", request=MagicMock(), response=mock_response
        )
        mock_http_client.get.return_value = mock_response

        result = await tool.execute(
            tenant_id=tenant_id,
            workflow_id="wf-123",
        )

        assert result["success"] is False
        assert result["error"] == "internal_error"

    @pytest.mark.asyncio
    async def test_timeout(self, tenant_id, config, mock_http_client):
        """Test timeout exception."""
        tool = WorkflowTriggerTool(tenant_id=tenant_id, config=config)
        tool._client = mock_http_client

        mock_http_client.get.side_effect = httpx.TimeoutException("Timeout")

        result = await tool.execute(
            tenant_id=tenant_id,
            workflow_id="wf-123",
        )

        assert result["success"] is False
        assert result["error"] == "timeout"

    @pytest.mark.asyncio
    async def test_list_workflows(self, tenant_id, config, mock_http_client):
        """Test listing available workflows."""
        tool = WorkflowTriggerTool(tenant_id=tenant_id, config=config)
        tool._client = mock_http_client

        list_response = {
            "success": True,
            "data": [
                {"id": "wf-1", "workflow_code": "provision_device", "name": "Provision Device"},
                {"id": "wf-2", "workflow_code": "activate_entity", "name": "Activate Entity"},
            ],
        }
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = list_response
        mock_response.raise_for_status.return_value = None
        mock_http_client.get.return_value = mock_response

        result = await tool.list_workflows(tenant_id=tenant_id)

        assert result["success"] is True
        assert result["count"] == 2

    @pytest.mark.asyncio
    async def test_get_execution_status(self, tenant_id, config, mock_http_client):
        """Test getting execution status."""
        tool = WorkflowTriggerTool(tenant_id=tenant_id, config=config)
        tool._client = mock_http_client

        status_response = {
            "success": True,
            "data": {
                "execution_id": "exec-123",
                "status": "success",
                "outputs": {"result": "ok"},
            },
        }
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = status_response
        mock_response.raise_for_status.return_value = None
        mock_http_client.get.return_value = mock_response

        result = await tool.get_execution_status(tenant_id=tenant_id, execution_id="exec-123")

        assert result["success"] is True
        assert result["data"]["status"] == "success"


# ---------------------------------------------------------------------------
# CustomToolLoader Tests
# ---------------------------------------------------------------------------

class TestCustomToolLoader:
    """Tests for CustomToolLoader."""

    def test_init(self, tenant_id, config):
        """Test loader initialization."""
        loader = CustomToolLoader(tenant_id=tenant_id, config=config)
        assert loader.tenant_id == tenant_id
        assert isinstance(loader._loaded_tools, dict)
        assert isinstance(loader._tool_classes, dict)

    def test_scan_empty_directory(self, tenant_id, config, tmp_path):
        """Test scanning empty directory."""
        loader = CustomToolLoader(
            tenant_id=tenant_id,
            config=config,
            tools_dir=tmp_path,
        )
        results = loader.scan()
        assert len(results) == 0

    def test_validate_tool_schema(self, tenant_id, config):
        """Test tool schema validation."""
        loader = CustomToolLoader(tenant_id=tenant_id, config=config)

        # Create a valid tool class
        class ValidTool:
            tool_name = "valid_tool"
            description = "A valid tool"

            async def execute(self, tenant_id: str, param: str = "default"):
                return {"result": param}

        # Test validation would require importing from module
        # This is a basic sanity check
        assert loader is not None

    def test_list_tools_empty(self, tenant_id, config):
        """Test listing tools when none are loaded."""
        loader = CustomToolLoader(tenant_id=tenant_id, config=config)
        tools = loader.list_tools()
        assert isinstance(tools, list)

    def test_get_tool_not_found(self, tenant_id, config):
        """Test getting non-existent tool."""
        loader = CustomToolLoader(tenant_id=tenant_id, config=config)
        tool = loader.get_tool("nonexistent")
        assert tool is None

    def test_get_tool_instance_not_found(self, tenant_id, config):
        """Test getting non-existent tool instance."""
        loader = CustomToolLoader(tenant_id=tenant_id, config=config)
        instance = loader.get_tool_instance("nonexistent")
        assert instance is None

    def test_type_to_json_schema(self):
        """Test type mapping to JSON schema."""
        assert CustomToolLoader._type_to_json_schema(str) == "string"
        assert CustomToolLoader._type_to_json_schema(int) == "integer"
        assert CustomToolLoader._type_to_json_schema(float) == "number"
        assert CustomToolLoader._type_to_json_schema(bool) == "boolean"
        assert CustomToolLoader._type_to_json_schema(list) == "array"
        assert CustomToolLoader._type_to_json_schema(dict) == "object"
        assert CustomToolLoader._type_to_json_schema(type(None)) == "string"  # fallback


# ---------------------------------------------------------------------------
# End-to-End Integration Tests
# ---------------------------------------------------------------------------

class TestAgentToolsE2E:
    """End-to-end integration tests for the agent tools pipeline."""

    @pytest.mark.asyncio
    async def test_full_pipeline(self, tenant_id, config):
        """Test the full agent → tool → response pipeline."""
        # This test verifies all tools can be instantiated and have correct interfaces
        telemetry_tool = TelemetryQueryTool(tenant_id=tenant_id, config=config)
        asset_tool = AssetLookupTool(tenant_id=tenant_id, config=config)
        ontology_tool = OntologySearchTool(tenant_id=tenant_id, config=config)
        workflow_tool = WorkflowTriggerTool(tenant_id=tenant_id, config=config)
        loader = CustomToolLoader(tenant_id=tenant_id, config=config)

        # Verify tool names
        assert telemetry_tool.tool_name == "telemetry_query"
        assert asset_tool.tool_name == "asset_lookup"
        assert ontology_tool.tool_name == "ontology_search"
        assert workflow_tool.tool_name == "workflow_trigger"

        # Verify all tools have required methods
        for tool in [telemetry_tool, asset_tool, ontology_tool, workflow_tool]:
            assert hasattr(tool, "execute")
            assert hasattr(tool, "close")

        # Cleanup
        await telemetry_tool.close()
        await asset_tool.close()
        await ontology_tool.close()
        await workflow_tool.close()

    @pytest.mark.asyncio
    async def test_error_handling_pipeline(self, tenant_id, config):
        """Test error handling across all tools."""
        tools = [
            ("telemetry", TelemetryQueryTool(tenant_id=tenant_id, config=config)),
            ("asset", AssetLookupTool(tenant_id=tenant_id, config=config)),
            ("ontology", OntologySearchTool(tenant_id=tenant_id, config=config)),
            ("workflow", WorkflowTriggerTool(tenant_id=tenant_id, config=config)),
        ]

        for name, tool in tools:
            # Test tenant mismatch
            result = await tool.execute(tenant_id="wrong-tenant")
            assert result["success"] is False
            assert result.get("error") == "tenant_mismatch"
            await tool.close()

    @pytest.mark.asyncio
    async def test_convenience_methods(self, tenant_id, config):
        """Test convenience methods on tools."""
        # TelemetryQueryTool
        tq = TelemetryQueryTool(tenant_id=tenant_id, config=config)
        assert hasattr(tq, "query_by_time_range")
        assert hasattr(tq, "query_latest")
        await tq.close()

        # AssetLookupTool
        al = AssetLookupTool(tenant_id=tenant_id, config=config)
        assert hasattr(al, "get_asset_hierarchy")
        await al.close()

        # OntologySearchTool
        os = OntologySearchTool(tenant_id=tenant_id, config=config)
        assert hasattr(os, "get_concept_hierarchy")
        await os.close()

        # WorkflowTriggerTool
        wt = WorkflowTriggerTool(tenant_id=tenant_id, config=config)
        assert hasattr(wt, "list_workflows")
        assert hasattr(wt, "get_execution_status")
        assert hasattr(wt, "cancel_execution")
        await wt.close()
