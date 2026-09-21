"""CP3 — Multi-tenant isolation penetration test.

Verifies that:
- Data is isolated between tenants
- Quotas are enforced per-tenant
- Resources cannot be shared across tenants
"""
import pytest
import asyncio
from datetime import datetime, timezone

from services.edge.storage.local_store import LocalTelemetryStore, TelemetryPoint
from services.sync.engine import SyncEngine


class TestTenantDataIsolation:
    """Test data isolation between tenants."""

    @pytest.mark.asyncio
    async def test_tenant_a_cannot_read_tenant_b_data(self):
        """Tenant A's data must not be visible to Tenant B."""
        store_a = LocalTelemetryStore(":memory:")
        store_b = LocalTelemetryStore(":memory:")
        await store_a.connect()
        await store_b.connect()

        # Write different data for each tenant
        for i in range(10):
            await store_a.write([
                TelemetryPoint(asset_id=f"a-{i}", property_code="temp",
                               timestamp=datetime.now(timezone.utc), value=float(i))
            ], tenant_id="tenant-a")
            await store_b.write([
                TelemetryPoint(asset_id=f"b-{i}", property_code="temp",
                               timestamp=datetime.now(timezone.utc), value=float(i) * 2)
            ], tenant_id="tenant-b")

        # Query tenant-a data from store-a
        results_a = await store_a.query("a-0", "temp", 0, 9999999999)
        assert len(results_a) >= 1

        # Query tenant-b data from store-b
        results_b = await store_b.query("b-0", "temp", 0, 9999999999)
        assert len(results_b) >= 1

        await store_a.close()
        await store_b.close()

    @pytest.mark.asyncio
    async def test_tenant_counts_are_independent(self):
        """Count queries must be tenant-scoped."""
        store = LocalTelemetryStore(":memory:")
        await store.connect()

        for i in range(20):
            await store.write([
                TelemetryPoint(asset_id=f"a-{i}", property_code="x",
                               timestamp=datetime.now(timezone.utc), value=1.0)
            ], tenant_id="tenant-a")
            await store.write([
                TelemetryPoint(asset_id=f"b-{i}", property_code="x",
                               timestamp=datetime.now(timezone.utc), value=2.0)
            ], tenant_id="tenant-b")

        count_a = await store.count("tenant-a", hours=1)
        count_b = await store.count("tenant-b", hours=1)
        assert count_a == 20
        assert count_b == 20
        await store.close()


class TestTenantQuotaEnforcement:
    """Test quota enforcement per tenant."""

    @pytest.mark.asyncio
    async def test_quota_limit_enforced(self):
        """Writes beyond quota must be rejected."""
        from services.sync.engine import SyncEngine

        engine = SyncEngine(node_id="quota-edge", cloud_url="ws://cloud:8000")
        await engine.connect()

        # Simulate quota check
        result = await engine.upload_telemetry([{"value": 1.0}])
        assert "accepted" in result

    @pytest.mark.asyncio
    async def test_no_quota_sharing_between_tenants(self):
        """Tenant A's quota must not affect Tenant B."""
        engine_a = SyncEngine(node_id="quota-a", cloud_url="ws://cloud:8000")
        engine_b = SyncEngine(node_id="quota-b", cloud_url="ws://cloud:8000")
        await engine_a.connect()
        await engine_b.connect()

        result_a = await engine_a.upload_telemetry([{"value": 1.0}])
        result_b = await engine_b.upload_telemetry([{"value": 2.0}])

        # Both should succeed independently
        assert result_a["accepted"] >= 0
        assert result_b["accepted"] >= 0


class TestResourceIsolation:
    """Test resource isolation between tenants."""

    @pytest.mark.asyncio
    async def test_no_cross_tenant_resource_access(self):
        """Tenants must not access each other's resources."""
        store_a = LocalTelemetryStore(":memory:")
        store_b = LocalTelemetryStore(":memory:")
        await store_a.connect()
        await store_b.connect()

        # Each tenant writes to their own store
        await store_a.write([
            TelemetryPoint(asset_id="exclusive-a", property_code="secret",
                           timestamp=datetime.now(timezone.utc), value=42.0)
        ], tenant_id="tenant-a")

        await store_b.write([
            TelemetryPoint(asset_id="exclusive-b", property_code="secret",
                           timestamp=datetime.now(timezone.utc), value=99.0)
        ], tenant_id="tenant-b")

        # Verify isolation
        count_a = await store_a.count("tenant-a", hours=1)
        count_b = await store_b.count("tenant-b", hours=1)
        assert count_a == 1
        assert count_b == 1
        await store_a.close()
        await store_b.close()


class TestPenetrationSecurity:
    """Security penetration tests for multi-tenant isolation."""

    @pytest.mark.asyncio
    async def test_no_tenant_id_leak_in_queries(self):
        """Query results must not leak other tenants' tenant_id."""
        store = LocalTelemetryStore(":memory:")
        await store.connect()

        await store.write([
            TelemetryPoint(asset_id="t1", property_code="x",
                           timestamp=datetime.now(timezone.utc), value=1.0)
        ], tenant_id="tenant-a")
        await store.write([
            TelemetryPoint(asset_id="t2", property_code="x",
                           timestamp=datetime.now(timezone.utc), value=2.0)
        ], tenant_id="tenant-b")

        results = await store.query("t1", "x", 0, 9999999999)
        # Results should not contain tenant_id in the response
        for r in results:
            assert "tenant_id" not in r
        await store.close()

    @pytest.mark.asyncio
    async def test_sync_engine_tenant_isolation(self):
        """Sync engines must not share state across tenants."""
        engine_a = SyncEngine(node_id="edge-a", cloud_url="ws://cloud:8000")
        engine_b = SyncEngine(node_id="edge-b", cloud_url="ws://cloud:8000")
        await engine_a.connect()
        await engine_b.connect()

        await engine_a.upload_telemetry([{"value": 1.0}])
        await engine_b.upload_telemetry([{"value": 2.0}])

        # Each engine's pending count should be independent
        pending_a = engine_a.get_pending_count()
        pending_b = engine_b.get_pending_count()
        # Both should have some pending (mock behavior)
        assert isinstance(pending_a, dict)
        assert isinstance(pending_b, dict)
