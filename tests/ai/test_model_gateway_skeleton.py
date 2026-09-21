"""Task 17 CP1 — Model Gateway skeleton smoke test."""
import pytest
from uuid import uuid4

from services.ai.model.gateway import ModelGateway
from services.ai.model.quota import TenantQuotaManager
from services.ai.model.cost import CostTracker
from services.ai.model.health import HealthChecker
from services.ai.audit.models import AIUsageLog, AIAuditLog


class TestModelGateway:
    def test_gateway_init(self):
        gw = ModelGateway()
        assert gw is not None


class TestTenantQuotaManager:
    def test_quota_init(self):
        qm = TenantQuotaManager(tenant_id=uuid4())
        assert qm.tenant_id is not None


class TestCostTracker:
    def test_tracker_init(self):
        ct = CostTracker()
        assert ct is not None


class TestHealthChecker:
    def test_checker_init(self):
        hc = HealthChecker()
        assert hc is not None


class TestAuditModels:
    def test_usage_log(self):
        log = AIUsageLog(
            tenant_id=uuid4(),
            trace_id="test-trace-1",
            model="gpt-4o",
            provider="openai",
            input_tokens=100,
            output_tokens=50,
        )
        assert log.total_tokens == 150
        assert log.success is True

    def test_audit_log(self):
        log = AIAuditLog(
            tenant_id=uuid4(),
            trace_id="test-trace-2",
            action="chat",
            resource_type="conversation",
            outcome="success",
        )
        assert log.action == "chat"
        assert log.outcome == "success"
