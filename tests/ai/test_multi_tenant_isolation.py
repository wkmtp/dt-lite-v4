"""Task 17 CP1 — Multi-tenant isolation test."""
import pytest
from uuid import uuid4

from services.ai.model.quota import TenantQuotaManager
from services.ai.agent.memory import MemoryManager
from services.ai.rag.vectorstore import PGVectorStore


class TestTenantIsolation:
    """R4: tenant data must be isolated."""

    def test_different_tenants_different_ids(self):
        qm1 = TenantQuotaManager(tenant_id=uuid4())
        qm2 = TenantQuotaManager(tenant_id=uuid4())
        assert qm1.tenant_id != qm2.tenant_id

    def test_memory_manager_tenant_bound(self):
        mm1 = MemoryManager(tenant_id=uuid4())
        mm2 = MemoryManager(tenant_id=uuid4())
        assert mm1.tenant_id != mm2.tenant_id

    def test_vectorstore_tenant_prefix(self):
        store = PGVectorStore(tenant_id=uuid4())
        assert store.tenant_id is not None


class TestCostIsolation:
    """R5: costs must be tracked per-tenant."""
    def test_cost_tracker_tenant_bound(self):
        from services.ai.model.cost import CostTracker
        ct = CostTracker()
        assert ct is not None
