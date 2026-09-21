"""Tests for Local Persistence storage."""
import pytest
import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

from services.edge.storage.local_store import (
    SQLiteMetadataStore,
    LocalTelemetryStore,
    TelemetryPoint,
)


class TestSQLiteMetadataStore:
    """Test SQLite metadata store."""

    @pytest.mark.asyncio
    async def test_connect_close(self):
        store = SQLiteMetadataStore(":memory:")
        await store.connect()
        await store.close()

    @pytest.mark.asyncio
    async def test_set_get_config(self):
        store = SQLiteMetadataStore(":memory:")
        await store.connect()
        await store.set_config("key1", {"nested": "value"})
        result = await store.get_config("key1")
        assert result == {"nested": "value"}
        await store.close()

    @pytest.mark.asyncio
    async def test_get_missing_config(self):
        store = SQLiteMetadataStore(":memory:")
        await store.connect()
        result = await store.get_config("missing")
        assert result is None
        await store.close()


class TestLocalTelemetryStore:
    """Test local telemetry storage."""

    @pytest.mark.asyncio
    async def test_connect_close(self):
        store = LocalTelemetryStore(":memory:")
        await store.connect()
        await store.close()

    @pytest.mark.asyncio
    async def test_write_and_query(self):
        store = LocalTelemetryStore(":memory:")
        await store.connect()

        points = [
            TelemetryPoint(
                asset_id="asset-1",
                property_code="temperature",
                timestamp=datetime.now(timezone.utc),
                value=25.5,
                quality="GOOD",
                source_adapter="modbus",
            )
            for _ in range(10)
        ]

        result = await store.write(points, tenant_id="tenant-1")
        assert result["accepted"] == 10
        assert result["rejected"] == 0

        # Query back
        import time
        now = time.time()
        results = await store.query("asset-1", "temperature", now - 3600, now)
        assert len(results) == 10

        await store.close()

    @pytest.mark.asyncio
    async def test_write_with_tenant_isolation(self):
        store = LocalTelemetryStore(":memory:")
        await store.connect()

        points = [
            TelemetryPoint(
                asset_id="asset-1",
                property_code="temperature",
                timestamp=datetime.now(timezone.utc),
                value=25.5,
            )
        ]

        await store.write(points, tenant_id="tenant-a")
        await store.write(points, tenant_id="tenant-b")

        # Count by tenant
        count_a = await store.count("tenant-a", hours=24)
        count_b = await store.count("tenant-b", hours=24)
        assert count_a == 1
        assert count_b == 1

        await store.close()

    @pytest.mark.asyncio
    async def test_get_latest(self):
        store = LocalTelemetryStore(":memory:")
        await store.connect()

        points = [
            TelemetryPoint(
                asset_id="asset-1",
                property_code="temperature",
                timestamp=datetime.now(timezone.utc),
                value=float(i),
            )
            for i in range(10)
        ]
        await store.write(points, tenant_id="tenant-1")

        latest = await store.get_latest("asset-1", "temperature", limit=5)
        assert len(latest) == 5

        await store.close()

    def test_telemetry_point_to_dict(self):
        point = TelemetryPoint(
            asset_id="asset-1",
            property_code="temp",
            timestamp=datetime.now(timezone.utc),
            value=25.5,
        )
        d = point.to_dict()
        assert d["asset_id"] == "asset-1"
        assert d["value"] == 25.5
        assert "timestamp" in d
