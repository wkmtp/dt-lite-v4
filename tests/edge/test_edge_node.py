"""Tests for Edge Node lifecycle management."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

from services.edge.core.node import (
    EdgeNode,
    NodeStatus,
    ComponentHealth,
    ResourceUsage,
    ResourceQuota,
    ProvisionRequest,
    ProvisionResponse,
    HeartbeatRequest,
    HeartbeatResponse,
    HealthResponse,
)


class TestEdgeNodeProvisioning:
    """Test edge node provisioning."""

    def test_create_node(self):
        node = EdgeNode(node_id="test-node", tenant_id="test-tenant")
        assert node.node_id == "test-node"
        assert node.tenant_id == "test-tenant"
        assert node.status == NodeStatus.PROVISIONING

    @pytest.mark.asyncio
    async def test_provision_success(self):
        node = EdgeNode(node_id="test-node")
        config = await node.provision("valid-token-123")
        assert node.status == NodeStatus.RUNNING
        assert "node_id" in config
        assert config["node_id"] == "test-node"

    @pytest.mark.asyncio
    async def test_provision_invalid_token(self):
        node = EdgeNode()
        with pytest.raises(ValueError, match="Invalid provisioning token"):
            await node.provision("short")

    @pytest.mark.asyncio
    async def test_provision_empty_token(self):
        node = EdgeNode()
        with pytest.raises(ValueError):
            await node.provision("")


class TestEdgeNodeHeartbeat:
    """Test edge node heartbeat."""

    @pytest.mark.asyncio
    async def test_heartbeat(self):
        node = EdgeNode(node_id="test-node")
        node.status = NodeStatus.RUNNING
        result = await node.heartbeat()
        assert result["ack"] is True
        assert "next_heartbeat_ms" in result

    @pytest.mark.asyncio
    async def test_start_stop_heartbeat_loop(self):
        node = EdgeNode(node_id="test-node")
        node.status = NodeStatus.RUNNING
        await node.start_heartbeat_loop(interval_ms=100)
        assert node._heartbeat_task is not None
        await node.stop()
        assert node.status == NodeStatus.STOPPED


class TestEdgeNodeResourceMonitoring:
    """Test resource monitoring and quota."""

    def test_update_resource_usage(self):
        node = EdgeNode()
        usage = ResourceUsage(cpu_percent=50.0, memory_bytes=1024*1024*500, disk_bytes=1024*1024*100)
        node.update_resource_usage(usage)
        assert node.resource_usage.cpu_percent == 50.0

    def test_check_resource_quota_within_limits(self):
        node = EdgeNode()
        node.resource_usage = ResourceUsage(cpu_percent=50.0, memory_bytes=500*1024*1024)
        node.resource_quota = ResourceQuota(memory_limit_bytes=2*1024*1024*1024)
        result = node.check_resource_quota()
        assert result["memory_ok"] is True

    def test_check_resource_quota_exceeded(self):
        node = EdgeNode()
        node.resource_usage = ResourceUsage(memory_bytes=1900*1024*1024)
        node.resource_quota = ResourceQuota(memory_limit_bytes=2*1024*1024*1024)
        result = node.check_resource_quota()
        assert result["memory_ok"] is False


class TestEdgeNodeHealth:
    """Test health reporting."""

    def test_get_health_summary(self):
        node = EdgeNode(node_id="test-node")
        node.status = NodeStatus.RUNNING
        node.health = {"database": ComponentHealth.HEALTHY, "cache": ComponentHealth.DEGRADED}
        summary = node.get_health_summary()
        assert summary["node_id"] == "test-node"
        assert summary["status"] == "running"
        assert "database" in summary["components"]


class TestPydanticSchemas:
    """Test Pydantic request/response schemas."""

    def test_provision_request(self):
        req = ProvisionRequest(token="valid-token-123")
        assert req.token == "valid-token-123"

    def test_provision_request_invalid_token(self):
        with pytest.raises(Exception):
            ProvisionRequest(token="short")

    def test_heartbeat_response(self):
        resp = HeartbeatResponse(ack=True, next_heartbeat_ms=30000)
        assert resp.ack is True

    def test_health_response(self):
        resp = HealthResponse(status="ok", version="4.18.0")
        assert resp.status == "ok"
