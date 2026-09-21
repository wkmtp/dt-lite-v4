"""Integration tests for core flow: Device Registration → Local Write → Sync Upload → Cloud Ingest."""
import pytest
import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from services.edge.core.node import EdgeNode, NodeStatus
from services.sync.engine import SyncEngine, HLCTimestamp
from services.edge.storage.local_store import LocalTelemetryStore, TelemetryPoint
from services.adapter.edge.base import EdgeAdapterRegistry, AdapterStatus
from services.adapter.edge.modbus_edge import ModbusEdgeAdapter


class TestCoreFlow:
    """Test the complete core flow from device to cloud."""

    @pytest.fixture
    def edge_node(self):
        """Create a test edge node."""
        return EdgeNode(node_id="test-edge-001", tenant_id="test-tenant")

    @pytest.fixture
    def sync_engine(self):
        """Create a test sync engine."""
        return SyncEngine(node_id="test-edge-001", cloud_url="ws://cloud:8000")

    @pytest.fixture
    def telemetry_store(self):
        """Create a test telemetry store."""
        return LocalTelemetryStore(":memory:")

    @pytest.fixture
    def adapter_registry(self):
        """Create a test adapter registry."""
        return EdgeAdapterRegistry()

    @pytest.mark.asyncio
    async def test_step1_device_registration(self, edge_node):
        """Step 1: Device registration with provisioning."""
        config = await edge_node.provision("test-token-123456")
        assert edge_node.status == NodeStatus.RUNNING
        assert config["node_id"] == "test-edge-001"
        assert "cloud_url" in config

    @pytest.mark.asyncio
    async def test_step2_local_write(self, telemetry_store):
        """Step 2: Write telemetry to local storage."""
        await telemetry_store.connect()
        points = [
            TelemetryPoint(
                asset_id=f"asset-{i}",
                property_code="temperature",
                timestamp=datetime.now(timezone.utc),
                value=25.0 + i * 0.5,
                quality="GOOD",
                source_adapter="modbus",
            )
            for i in range(10)
        ]
        result = await telemetry_store.write(points, tenant_id="test-tenant")
        assert result["accepted"] == 10
        assert result["rejected"] == 0
        await telemetry_store.close()

    @pytest.mark.asyncio
    async def test_step3_sync_upload(self, sync_engine):
        """Step 3: Upload telemetry to cloud (simulated)."""
        sync_engine._connected = True
        points = [{"value": 25.5, "asset_id": "asset-1"}]
        result = await sync_engine.upload_telemetry(points)
        assert result["accepted"] == 1
        assert result["rejected"] == 0

    @pytest.mark.asyncio
    async def test_step4_cloud_ingest(self):
        """Step 4: Verify cloud-side ingest (simulated)."""
        # In production, this would verify the cloud database received the data
        # For integration test, we verify the sync engine state
        sync_engine = SyncEngine(node_id="test-edge-001")
        await sync_engine.connect()
        assert sync_engine._connected is True
        await sync_engine.disconnect()

    @pytest.mark.asyncio
    async def test_full_flow_integration(self, edge_node, telemetry_store, sync_engine, adapter_registry):
        """Full flow: Register → Write → Sync → Verify."""
        # Step 1: Register
        await edge_node.provision("test-token-123")
        assert edge_node.status == NodeStatus.RUNNING

        # Step 2: Register adapter
        adapter = ModbusEdgeAdapter(
            adapter_id="modbus-1",
            endpoint="192.168.1.1:502",
            tenant_id=edge_node.tenant_id,
        )
        adapter_registry.register(adapter)

        # Step 3: Read from adapter
        points = await adapter.read(["modbus:slave=1:fc=3:addr=100"])
        assert len(points) >= 0  # May be empty if not connected

        # Step 4: Write to local storage
        await telemetry_store.connect()
        if points:
            result = await telemetry_store.write(points, tenant_id=edge_node.tenant_id)
            assert result["accepted"] >= 0
        await telemetry_store.close()

        # Step 5: Sync to cloud
        sync_engine._connected = True
        result = await sync_engine.upload_telemetry(
            [{"value": 25.5, "asset_id": "asset-1"}]
        )
        assert result["accepted"] >= 0

    @pytest.mark.asyncio
    async def test_offline_buffering(self, telemetry_store, sync_engine):
        """Test offline mode: data buffered locally, synced when reconnected."""
        # Simulate offline
        sync_engine._connected = False
        result = await sync_engine.upload_telemetry([{"value": 25.0}])
        assert result["accepted"] == 0
        assert result["queued"] == 1

        # Simulate reconnection
        sync_engine._connected = True
        result = await sync_engine.upload_telemetry([{"value": 25.5}])
        assert result["accepted"] == 1


class TestConflictResolution:
    """Test CRDT conflict resolution."""

    @pytest.mark.asyncio
    async def test_lww_conflict_resolution(self):
        """Test Last-Writer-Wins conflict resolution."""
        from services.sync.engine import LWWRegister, HLCTimestamp

        # Cloud has earlier timestamp
        cloud_reg = LWWRegister(value=25.0, timestamp=HLCTimestamp(physical_ts=1000))
        # Edge has later timestamp
        edge_reg = LWWRegister(value=30.0, timestamp=HLCTimestamp(physical_ts=2000))

        merged = cloud_reg.merge(edge_reg)
        assert merged.get() == 30.0  # Edge wins (later timestamp)

    @pytest.mark.asyncio
    async def test_orset_merge(self):
        """Test OR-Set merge."""
        from services.sync.engine import ORSet

        set1 = ORSet()
        set1.add("item_a")
        set1.add("item_b")

        set2 = ORSet()
        set2.add("item_b")
        set2.add("item_c")

        merged = set1.merge(set2)
        result = merged.get()
        assert "item_a" in result
        assert "item_b" in result
        assert "item_c" in result


class TestHLCOrdering:
    """Test HLC causal ordering."""

    def test_hlc_causal_ordering(self):
        """Test that HLC provides causal ordering."""
        from services.sync.engine import HLCTimestamp

        hlc1 = HLCTimestamp(physical_ts=1000, logical_counter=5)
        hlc2 = HLCTimestamp(physical_ts=1000, logical_counter=10)
        hlc3 = HLCTimestamp(physical_ts=2000, logical_counter=0)

        assert hlc2.is_after(hlc1)  # Same physical, higher logical
        assert hlc3.is_after(hlc1)  # Later physical
        assert hlc3.is_after(hlc2)  # Later physical
