"""Tests for Sync Engine with HLC and CRDT."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from services.sync.engine import (
    HLCTimestamp,
    LWWRegister,
    ORSet,
    SyncConflict,
    SyncEngine,
)


class TestHLCTimestamp:
    """Test Hybrid Logical Clock."""

    def test_create_hlc(self):
        hlc = HLCTimestamp.now(node_id="node-1")
        assert hlc.node_id == "node-1"
        assert hlc.physical_ts > 0
        assert hlc.logical_counter == 0

    def test_increment(self):
        hlc = HLCTimestamp(physical_ts=1000, logical_counter=5, node_id="node-1")
        incremented = hlc.increment()
        assert incremented.logical_counter == 6
        assert incremented.physical_ts == 1000

    def test_merge(self):
        hlc1 = HLCTimestamp(physical_ts=1000, logical_counter=5, node_id="node-1")
        hlc2 = HLCTimestamp(physical_ts=1200, logical_counter=3, node_id="node-2")
        merged = hlc1.merge(hlc2)
        assert merged.physical_ts == 1200  # max
        assert merged.logical_counter == 6  # max + 1

    def test_is_after(self):
        hlc1 = HLCTimestamp(physical_ts=1000, logical_counter=5)
        hlc2 = HLCTimestamp(physical_ts=500, logical_counter=10)
        assert hlc1.is_after(hlc2) is True
        assert hlc2.is_after(hlc1) is False

    def test_to_dict_from_dict(self):
        hlc = HLCTimestamp(physical_ts=1000, logical_counter=5, node_id="node-1")
        d = hlc.to_dict()
        assert d["physical_ts"] == 1000
        hlc2 = HLCTimestamp.from_dict(d)
        assert hlc2.physical_ts == 1000


class TestLWWRegister:
    """Test Last-Writer-Wins Register CRDT."""

    def test_create_register(self):
        reg = LWWRegister(value="initial")
        assert reg.get() == "initial"

    def test_update_with_earlier_timestamp(self):
        reg = LWWRegister(value="old", timestamp=HLCTimestamp(physical_ts=1000))
        new_hlc = HLCTimestamp(physical_ts=500)  # earlier
        reg.update("new", new_hlc)
        assert reg.get() == "old"  # unchanged

    def test_update_with_later_timestamp(self):
        reg = LWWRegister(value="old", timestamp=HLCTimestamp(physical_ts=500))
        new_hlc = HLCTimestamp(physical_ts=1000)  # later
        reg.update("new", new_hlc)
        assert reg.get() == "new"

    def test_merge(self):
        reg1 = LWWRegister(value="a", timestamp=HLCTimestamp(physical_ts=1000))
        reg2 = LWWRegister(value="b", timestamp=HLCTimestamp(physical_ts=2000))
        merged = reg1.merge(reg2)
        assert merged.get() == "b"  # later wins


class TestORSet:
    """Test Observed-Remove Set CRDT."""

    def test_add_and_get(self):
        s = ORSet()
        s.add("element1")
        assert "element1" in s.get()

    def test_remove(self):
        s = ORSet()
        s.add("element1")
        s.remove("element1")
        assert "element1" not in s.get()

    def test_merge(self):
        s1 = ORSet()
        s1.add("a")
        s1.add("b")
        s2 = ORSet()
        s2.add("b")
        s2.add("c")
        merged = s1.merge(s2)
        result = merged.get()
        assert "a" in result
        assert "b" in result
        assert "c" in result


class TestSyncEngine:
    """Test Sync Engine."""

    def test_create_engine(self):
        engine = SyncEngine(node_id="edge-1", cloud_url="ws://cloud:8000")
        assert engine.node_id == "edge-1"
        assert engine.hlc is not None

    @pytest.mark.asyncio
    async def test_upload_when_disconnected(self):
        engine = SyncEngine(node_id="edge-1")
        result = await engine.upload_telemetry([{"value": 1.0}])
        assert result["accepted"] == 0
        assert result["queued"] == 1

    @pytest.mark.asyncio
    async def test_upload_when_connected(self):
        engine = SyncEngine(node_id="edge-1")
        engine._connected = True
        result = await engine.upload_telemetry([{"value": 1.0}, {"value": 2.0}])
        assert result["accepted"] == 2
        assert result["rejected"] == 0

    @pytest.mark.asyncio
    async def test_detect_conflict_same_value(self):
        engine = SyncEngine(node_id="edge-1")
        conflict = await engine.detect_conflict(
            key="temp",
            cloud_value=25.0,
            edge_value=25.0,
            cloud_hlc=HLCTimestamp(physical_ts=1000),
            edge_hlc=HLCTimestamp(physical_ts=500),
        )
        assert conflict is None  # no conflict

    @pytest.mark.asyncio
    async def test_detect_conflict_different_values(self):
        engine = SyncEngine(node_id="edge-1")
        conflict = await engine.detect_conflict(
            key="temp",
            cloud_value=25.0,
            edge_value=30.0,
            cloud_hlc=HLCTimestamp(physical_ts=1000),
            edge_hlc=HLCTimestamp(physical_ts=500),
        )
        assert conflict is not None
        assert conflict.key == "temp"

    @pytest.mark.asyncio
    async def test_resolve_conflict_lww(self):
        engine = SyncEngine(node_id="edge-1")
        conflict = SyncConflict(
            key="temp",
            cloud_value=25.0,
            edge_value=30.0,
            cloud_hlc=HLCTimestamp(physical_ts=1000),
            edge_hlc=HLCTimestamp(physical_ts=500),
            strategy="lww",
        )
        resolved = await engine.resolve_conflict(conflict)
        # cloud has later timestamp
        assert resolved == 25.0

    def test_get_pending_count(self):
        engine = SyncEngine(node_id="edge-1")
        count = engine.get_pending_count()
        assert "pending_uploads" in count
        assert "pending_commands" in count


class TestSyncConflict:
    """Test SyncConflict dataclass."""

    def test_create_conflict(self):
        conflict = SyncConflict(
            key="test",
            cloud_value=1.0,
            edge_value=2.0,
            cloud_hlc=HLCTimestamp(physical_ts=1000),
            edge_hlc=HLCTimestamp(physical_ts=500),
        )
        assert conflict.key == "test"
        assert conflict.strategy == "lww"
