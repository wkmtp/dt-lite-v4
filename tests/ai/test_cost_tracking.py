"""Tests for CostTracker — token counting, cost estimation, alerts."""

import pytest
import asyncio
from unittest.mock import patch

from services.ai.model.cost import CostTracker, CostRecord, CostAlert


@pytest.fixture
def cost_tracker():
    """Create a CostTracker instance."""
    return CostTracker()


class TestCostCalculation:
    """Test cost calculation for different models."""

    def test_openai_gpt4o_cost(self, cost_tracker):
        """Calculate cost for GPT-4o."""
        cost = cost_tracker.calculate_cost(
            model="gpt-4o",
            input_tokens=1000,
            output_tokens=500,
            provider="openai",
        )
        # gpt-4o: prompt=2.50/1M, completion=10.00/1M
        expected = (1000 * 2.50 / 1_000_000) + (500 * 10.00 / 1_000_000)
        assert abs(cost - expected) < 0.000001

    def test_openai_gpt4o_mini_cost(self, cost_tracker):
        """Calculate cost for GPT-4o-mini."""
        cost = cost_tracker.calculate_cost(
            model="gpt-4o-mini",
            input_tokens=1000,
            output_tokens=500,
            provider="openai",
        )
        # gpt-4o-mini: prompt=0.15/1M, completion=0.60/1M
        expected = (1000 * 0.15 / 1_000_000) + (500 * 0.60 / 1_000_000)
        assert abs(cost - expected) < 0.000001

    def test_openai_gpt35_cost(self, cost_tracker):
        """Calculate cost for GPT-3.5-Turbo."""
        cost = cost_tracker.calculate_cost(
            model="gpt-3.5-turbo",
            input_tokens=1000,
            output_tokens=500,
            provider="openai",
        )
        # gpt-3.5-turbo: prompt=0.50/1M, completion=1.50/1M
        expected = (1000 * 0.50 / 1_000_000) + (500 * 1.50 / 1_000_000)
        assert abs(cost - expected) < 0.000001

    def test_ollama_free(self, cost_tracker):
        """Ollama models should be free."""
        cost = cost_tracker.calculate_cost(
            model="llama3.2",
            input_tokens=1000,
            output_tokens=500,
            provider="ollama",
        )
        assert cost == 0.0

    def test_anthropic_claude_cost(self, cost_tracker):
        """Calculate cost for Claude model."""
        cost = cost_tracker.calculate_cost(
            model="claude-3-5-sonnet-20241022",
            input_tokens=1000,
            output_tokens=500,
            provider="anthropic",
        )
        # claude-3-5-sonnet: prompt=3.00/1M, completion=15.00/1M
        expected = (1000 * 3.00 / 1_000_000) + (500 * 15.00 / 1_000_000)
        assert abs(cost - expected) < 0.000001

    def test_unknown_model_zero_cost(self, cost_tracker):
        """Unknown model/provider should return zero cost."""
        cost = cost_tracker.calculate_cost(
            model="unknown-model",
            input_tokens=1000,
            output_tokens=500,
            provider="unknown-provider",
        )
        assert cost == 0.0

    def test_zero_tokens(self, cost_tracker):
        """Zero tokens should result in zero cost."""
        cost = cost_tracker.calculate_cost(
            model="gpt-4o",
            input_tokens=0,
            output_tokens=0,
            provider="openai",
        )
        assert cost == 0.0


class TestCostTracking:
    """Test cost recording and retrieval."""

    @pytest.mark.asyncio
    async def test_track_single_request(self, cost_tracker):
        """Track a single cost record."""
        record = await cost_tracker.track(
            tenant_id="tenant-1",
            user_id="user-1",
            trace_id="trace-1",
            provider="openai",
            model="gpt-4o-mini",
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150,
            cost_usd=0.0000225,
        )
        assert record.tenant_id == "tenant-1"
        assert record.total_tokens == 150
        assert record.cost_usd == 0.0000225

    @pytest.mark.asyncio
    async def test_track_multiple_requests(self, cost_tracker):
        """Track multiple cost records."""
        await cost_tracker.track(
            tenant_id="tenant-1",
            user_id="user-1",
            trace_id="trace-1",
            provider="openai",
            model="gpt-4o-mini",
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150,
            cost_usd=0.0000225,
        )
        await cost_tracker.track(
            tenant_id="tenant-1",
            user_id="user-1",
            trace_id="trace-2",
            provider="openai",
            model="gpt-4o-mini",
            prompt_tokens=200,
            completion_tokens=100,
            total_tokens=300,
            cost_usd=0.000045,
        )

        history = await cost_tracker.get_tenant_history("tenant-1")
        assert len(history) == 2

    @pytest.mark.asyncio
    async def test_get_daily_cost(self, cost_tracker):
        """Get daily cost for a tenant."""
        await cost_tracker.track(
            tenant_id="tenant-1",
            user_id="user-1",
            trace_id="trace-1",
            provider="openai",
            model="gpt-4o-mini",
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150,
            cost_usd=0.001,
        )
        await cost_tracker.track(
            tenant_id="tenant-1",
            user_id="user-1",
            trace_id="trace-2",
            provider="openai",
            model="gpt-4o-mini",
            prompt_tokens=200,
            completion_tokens=100,
            total_tokens=300,
            cost_usd=0.002,
        )

        daily_cost = await cost_tracker.get_daily_cost("tenant-1")
        assert abs(daily_cost - 0.003) < 0.0001

    @pytest.mark.asyncio
    async def test_get_monthly_cost(self, cost_tracker):
        """Get monthly cost for a tenant."""
        await cost_tracker.track(
            tenant_id="tenant-1",
            user_id="user-1",
            trace_id="trace-1",
            provider="openai",
            model="gpt-4o-mini",
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150,
            cost_usd=0.001,
        )

        monthly_cost = await cost_tracker.get_monthly_cost("tenant-1")
        assert abs(monthly_cost - 0.001) < 0.0001

    @pytest.mark.asyncio
    async def test_get_daily_tokens(self, cost_tracker):
        """Get daily token count for a tenant."""
        await cost_tracker.track(
            tenant_id="tenant-1",
            user_id="user-1",
            trace_id="trace-1",
            provider="openai",
            model="gpt-4o-mini",
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150,
            cost_usd=0.001,
        )
        await cost_tracker.track(
            tenant_id="tenant-1",
            user_id="user-1",
            trace_id="trace-2",
            provider="openai",
            model="gpt-4o-mini",
            prompt_tokens=200,
            completion_tokens=100,
            total_tokens=300,
            cost_usd=0.002,
        )

        daily_tokens = await cost_tracker.get_daily_tokens("tenant-1")
        assert daily_tokens == 450

    @pytest.mark.asyncio
    async def test_get_monthly_tokens(self, cost_tracker):
        """Get monthly token count for a tenant."""
        await cost_tracker.track(
            tenant_id="tenant-1",
            user_id="user-1",
            trace_id="trace-1",
            provider="openai",
            model="gpt-4o-mini",
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150,
            cost_usd=0.001,
        )

        monthly_tokens = await cost_tracker.get_monthly_tokens("tenant-1")
        assert monthly_tokens == 150

    @pytest.mark.asyncio
    async def test_get_all_tenants_usage(self, cost_tracker):
        """Get usage for all tenants."""
        await cost_tracker.track(
            tenant_id="tenant-1",
            user_id="user-1",
            trace_id="trace-1",
            provider="openai",
            model="gpt-4o-mini",
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150,
            cost_usd=0.001,
        )
        await cost_tracker.track(
            tenant_id="tenant-2",
            user_id="user-2",
            trace_id="trace-2",
            provider="ollama",
            model="llama3.2",
            prompt_tokens=200,
            completion_tokens=100,
            total_tokens=300,
            cost_usd=0.0,
        )

        usage = await cost_tracker.get_all_tenants_usage()
        assert "tenant-1" in usage
        assert "tenant-2" in usage
        assert usage["tenant-1"]["daily_cost_usd"] == 0.001
        assert usage["tenant-2"]["daily_cost_usd"] == 0.0

    @pytest.mark.asyncio
    async def test_filter_by_provider(self, cost_tracker):
        """Filter history by provider."""
        await cost_tracker.track(
            tenant_id="tenant-1",
            user_id="user-1",
            trace_id="trace-1",
            provider="openai",
            model="gpt-4o-mini",
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150,
            cost_usd=0.001,
        )
        await cost_tracker.track(
            tenant_id="tenant-1",
            user_id="user-1",
            trace_id="trace-2",
            provider="ollama",
            model="llama3.2",
            prompt_tokens=200,
            completion_tokens=100,
            total_tokens=300,
            cost_usd=0.0,
        )

        history = await cost_tracker.get_tenant_history("tenant-1", provider="ollama")
        assert len(history) == 1
        assert history[0].provider == "ollama"

    @pytest.mark.asyncio
    async def test_filter_by_model(self, cost_tracker):
        """Filter history by model."""
        await cost_tracker.track(
            tenant_id="tenant-1",
            user_id="user-1",
            trace_id="trace-1",
            provider="openai",
            model="gpt-4o-mini",
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150,
            cost_usd=0.001,
        )
        await cost_tracker.track(
            tenant_id="tenant-1",
            user_id="user-1",
            trace_id="trace-2",
            provider="openai",
            model="gpt-4o",
            prompt_tokens=200,
            completion_tokens=100,
            total_tokens=300,
            cost_usd=0.002,
        )

        history = await cost_tracker.get_tenant_history("tenant-1", model="gpt-4o")
        assert len(history) == 1
        assert history[0].model == "gpt-4o"


class TestBudgetAlerts:
    """Test budget alert thresholds."""

    @pytest.mark.asyncio
    async def test_no_alert_when_under_threshold(self, cost_tracker):
        """No alert when usage is below threshold."""
        await cost_tracker.track(
            tenant_id="tenant-1",
            user_id="user-1",
            trace_id="trace-1",
            provider="openai",
            model="gpt-4o-mini",
            prompt_tokens=10,
            completion_tokens=10,
            total_tokens=20,
            cost_usd=0.000003,
        )

        alerts = cost_tracker.check_and_emit_alert(
            tenant_id="tenant-1",
            daily_tokens=100,
            daily_budget_tokens=10000,
            monthly_tokens=500,
            monthly_budget_tokens=100000,
            daily_cost=0.01,
            daily_budget_usd=10.0,
            monthly_cost=0.05,
            monthly_budget_usd=100.0,
        )
        assert len(alerts) == 0

    @pytest.mark.asyncio
    async def test_daily_token_alert(self, cost_tracker):
        """Alert when daily token usage exceeds threshold."""
        alerts = cost_tracker.check_and_emit_alert(
            tenant_id="tenant-1",
            daily_tokens=8000,  # 80% of 10000
            daily_budget_tokens=10000,
            monthly_tokens=500,
            monthly_budget_tokens=100000,
            daily_cost=0.01,
            daily_budget_usd=10.0,
            monthly_cost=0.05,
            monthly_budget_usd=100.0,
        )
        assert len(alerts) == 1
        assert alerts[0].alert_type == "daily_token_budget"
        assert alerts[0].tenant_id == "tenant-1"

    @pytest.mark.asyncio
    async def test_monthly_token_alert(self, cost_tracker):
        """Alert when monthly token usage exceeds threshold."""
        alerts = cost_tracker.check_and_emit_alert(
            tenant_id="tenant-1",
            daily_tokens=100,
            daily_budget_tokens=10000,
            monthly_tokens=80000,  # 80% of 100000
            monthly_budget_tokens=100000,
            daily_cost=0.01,
            daily_budget_usd=10.0,
            monthly_cost=0.05,
            monthly_budget_usd=100.0,
        )
        assert len(alerts) == 1
        assert alerts[0].alert_type == "monthly_token_budget"

    @pytest.mark.asyncio
    async def test_daily_cost_alert(self, cost_tracker):
        """Alert when daily cost exceeds threshold."""
        alerts = cost_tracker.check_and_emit_alert(
            tenant_id="tenant-1",
            daily_tokens=100,
            daily_budget_tokens=10000,
            monthly_tokens=500,
            monthly_budget_tokens=100000,
            daily_cost=8.0,  # 80% of 10.0
            daily_budget_usd=10.0,
            monthly_cost=0.05,
            monthly_budget_usd=100.0,
        )
        assert len(alerts) == 1
        assert alerts[0].alert_type == "daily_cost_budget"

    @pytest.mark.asyncio
    async def test_monthly_cost_alert(self, cost_tracker):
        """Alert when monthly cost exceeds threshold."""
        alerts = cost_tracker.check_and_emit_alert(
            tenant_id="tenant-1",
            daily_tokens=100,
            daily_budget_tokens=10000,
            monthly_tokens=500,
            monthly_budget_tokens=100000,
            daily_cost=0.01,
            daily_budget_usd=10.0,
            monthly_cost=80.0,  # 80% of 100.0
            monthly_budget_usd=100.0,
        )
        assert len(alerts) == 1
        assert alerts[0].alert_type == "monthly_cost_budget"

    @pytest.mark.asyncio
    async def test_multiple_alerts(self, cost_tracker):
        """Multiple alerts can be triggered simultaneously."""
        alerts = cost_tracker.check_and_emit_alert(
            tenant_id="tenant-1",
            daily_tokens=8000,
            daily_budget_tokens=10000,
            monthly_tokens=80000,
            monthly_budget_tokens=100000,
            daily_cost=8.0,
            daily_budget_usd=10.0,
            monthly_cost=80.0,
            monthly_budget_usd=100.0,
        )
        assert len(alerts) == 4  # All four alerts triggered

    @pytest.mark.asyncio
    async def test_alert_duplicate_prevention(self, cost_tracker):
        """Alert should only be sent once per day/month."""
        alerts1 = cost_tracker.check_and_emit_alert(
            tenant_id="tenant-1",
            daily_tokens=8000,
            daily_budget_tokens=10000,
            monthly_tokens=80000,
            monthly_budget_tokens=100000,
            daily_cost=8.0,
            daily_budget_usd=10.0,
            monthly_cost=80.0,
            monthly_budget_usd=100.0,
        )
        assert len(alerts1) == 4

        # Second call should not generate duplicate alerts
        alerts2 = cost_tracker.check_and_emit_alert(
            tenant_id="tenant-1",
            daily_tokens=8000,
            daily_budget_tokens=10000,
            monthly_tokens=80000,
            monthly_budget_tokens=100000,
            daily_cost=8.0,
            daily_budget_usd=10.0,
            monthly_cost=80.0,
            monthly_budget_usd=100.0,
        )
        assert len(alerts2) == 0

    @pytest.mark.asyncio
    async def test_custom_alert_threshold(self, cost_tracker):
        """Custom alert thresholds should work."""
        cost_tracker.set_alert_thresholds(daily_pct=0.5, monthly_pct=0.5)

        alerts = cost_tracker.check_and_emit_alert(
            tenant_id="tenant-1",
            daily_tokens=5000,  # 50% of 10000
            daily_budget_tokens=10000,
            monthly_tokens=50000,  # 50% of 100000
            monthly_budget_tokens=100000,
            daily_cost=5.0,  # 50% of 10.0
            daily_budget_usd=10.0,
            monthly_cost=50.0,  # 50% of 100.0
            monthly_budget_usd=100.0,
        )
        assert len(alerts) == 4


class TestResetFunctions:
    """Test reset/cleanup functions."""

    @pytest.mark.asyncio
    async def test_reset_records(self, cost_tracker):
        """Reset should clear all records."""
        await cost_tracker.track(
            tenant_id="tenant-1",
            user_id="user-1",
            trace_id="trace-1",
            provider="openai",
            model="gpt-4o-mini",
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150,
            cost_usd=0.001,
        )

        cost_tracker.reset_records("tenant-1")

        daily_cost = await cost_tracker.get_daily_cost("tenant-1")
        assert daily_cost == 0.0

    @pytest.mark.asyncio
    async def test_reset_all_records(self, cost_tracker):
        """Reset all records for all tenants."""
        await cost_tracker.track(
            tenant_id="tenant-1",
            user_id="user-1",
            trace_id="trace-1",
            provider="openai",
            model="gpt-4o-mini",
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150,
            cost_usd=0.001,
        )
        await cost_tracker.track(
            tenant_id="tenant-2",
            user_id="user-2",
            trace_id="trace-2",
            provider="ollama",
            model="llama3.2",
            prompt_tokens=200,
            completion_tokens=100,
            total_tokens=300,
            cost_usd=0.0,
        )

        cost_tracker.reset_all()

        usage = await cost_tracker.get_all_tenants_usage()
        assert len(usage) == 0

    @pytest.mark.asyncio
    async def test_reset_alerts(self, cost_tracker):
        """Reset should clear sent alerts."""
        cost_tracker.check_and_emit_alert(
            tenant_id="tenant-1",
            daily_tokens=8000,
            daily_budget_tokens=10000,
            monthly_tokens=500,
            monthly_budget_tokens=100000,
            daily_cost=8.0,
            daily_budget_usd=10.0,
            monthly_cost=0.05,
            monthly_budget_usd=100.0,
        )

        cost_tracker.reset_alerts("tenant-1")

        # Should be able to alert again
        alerts = cost_tracker.check_and_emit_alert(
            tenant_id="tenant-1",
            daily_tokens=8000,
            daily_budget_tokens=10000,
            monthly_tokens=500,
            monthly_budget_tokens=100000,
            daily_cost=8.0,
            daily_budget_usd=10.0,
            monthly_cost=0.05,
            monthly_budget_usd=100.0,
        )
        assert len(alerts) == 1


class TestCostRecord:
    """Test CostRecord dataclass."""

    def test_create_record(self):
        record = CostRecord(
            tenant_id="tenant-1",
            user_id="user-1",
            trace_id="trace-1",
            provider="openai",
            model="gpt-4o-mini",
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150,
            cost_usd=0.0000225,
            ts=__import__('datetime').datetime.now(__import__('datetime').timezone.utc),
        )
        assert record.total_tokens == 150
        assert record.cost_usd == 0.0000225


class TestIntegration:
    """Integration tests for cost tracking workflow."""

    @pytest.mark.asyncio
    async def test_full_workflow(self, cost_tracker):
        """Test full cost tracking workflow."""
        # Track several requests
        for i in range(5):
            await cost_tracker.track(
                tenant_id="tenant-1",
                user_id="user-1",
                trace_id=f"trace-{i}",
                provider="openai",
                model="gpt-4o-mini",
                prompt_tokens=100,
                completion_tokens=50,
                total_tokens=150,
                cost_usd=0.0000225,
            )

        # Check daily totals
        daily_tokens = await cost_tracker.get_daily_tokens("tenant-1")
        daily_cost = await cost_tracker.get_daily_cost("tenant-1")
        assert daily_tokens == 750
        assert abs(daily_cost - 0.0001125) < 0.00001

        # Check history
        history = await cost_tracker.get_tenant_history("tenant-1")
        assert len(history) == 5

        # Check alerts
        alerts = cost_tracker.check_and_emit_alert(
            tenant_id="tenant-1",
            daily_tokens=daily_tokens,
            daily_budget_tokens=10000,
            monthly_tokens=daily_tokens,
            monthly_budget_tokens=100000,
            daily_cost=daily_cost,
            daily_budget_usd=10.0,
            monthly_cost=daily_cost,
            monthly_budget_usd=100.0,
        )
        # Should not alert (well under threshold)
        assert len(alerts) == 0
