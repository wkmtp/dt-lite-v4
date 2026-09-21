"""Tests for TenantQuotaManager — RPM/TPM/budget enforcement with in-memory fallback."""

import pytest
import asyncio
from unittest.mock import AsyncMock, patch

from services.ai.model.quota import (
    TenantQuotaManager,
    QuotaConfig,
    QuotaCheckResult,
    _InMemoryQuota,
    _MODEL_PRICES,
)


@pytest.fixture
def quota_manager():
    qm = TenantQuotaManager(redis_url="redis://localhost:9999")
    with patch.object(qm, 'connect', new_callable=AsyncMock) as mock_connect:
        mock_connect.side_effect = Exception("Redis unavailable")
    return qm


@pytest.fixture
def tenant_config():
    return QuotaConfig(
        rpm=10,
        tpm=1000,
        daily_budget_tokens=5000,
        monthly_budget_tokens=50000,
        daily_budget_usd=5.0,
        monthly_budget_usd=50.0,
    )


class TestInMemoryQuota:
    def test_increment_and_get(self):
        mq = _InMemoryQuota()
        assert mq.get("tenant1", "key") == 0
        assert mq.increment("tenant1", "key", 5) == 5
        assert mq.get("tenant1", "key") == 5

    def test_add_cost(self):
        mq = _InMemoryQuota()
        assert mq.get_cost("tenant1", "cost") == 0.0
        assert mq.add_cost("tenant1", "cost", 0.5) == 0.5


class TestQuotaConfig:
    def test_default_config(self):
        cfg = QuotaConfig()
        assert cfg.rpm == 60
        assert cfg.tpm == 100_000
        assert cfg.daily_budget_usd == 10.0


class TestModelPrices:
    def test_openai_pricing(self):
        prices = _MODEL_PRICES.get("openai", {}).get("gpt-4o", {})
        assert prices["prompt"] > 0

    def test_ollama_free(self):
        prices = _MODEL_PRICES.get("ollama", {}).get("llama3.2", {})
        assert prices["prompt"] == 0.0


class TestQuotaManager:
    @pytest.mark.asyncio
    async def test_create_manager(self):
        qm = TenantQuotaManager()
        assert qm is not None

    @pytest.mark.asyncio
    async def test_set_and_get_quota(self, quota_manager, tenant_config):
        quota_manager.set_quota("tenant-1", tenant_config)
        cfg = quota_manager.get_config("tenant-1")
        assert cfg.rpm == 10

    @pytest.mark.asyncio
    async def test_check_allowed_under_limits(self, quota_manager, tenant_config):
        quota_manager.set_quota("tenant-1", tenant_config)
        result = await quota_manager.check_and_consume(
            tenant_id="tenant-1",
            model="gpt-4o-mini",
            provider="openai",
            prompt_tokens=100,
            completion_tokens=50,
        )
        assert result.allowed is True

    @pytest.mark.asyncio
    async def test_check_price(self, quota_manager):
        cost = quota_manager.check_price(
            model="gpt-4o-mini", provider="openai",
            prompt_tokens=1000, completion_tokens=500,
        )
        assert cost >= 0

    @pytest.mark.asyncio
    async def test_rpm_limit_enforcement(self, quota_manager, tenant_config):
        quota_manager.set_quota("tenant-1", tenant_config)
        for _ in range(10):
            result = await quota_manager.check_and_consume(
                tenant_id="tenant-1", model="gpt-4o-mini", provider="openai",
                prompt_tokens=10, completion_tokens=10,
            )
            assert result.allowed is True
        result = await quota_manager.check_and_consume(
            tenant_id="tenant-1", model="gpt-4o-mini", provider="openai",
            prompt_tokens=10, completion_tokens=10,
        )
        assert result.allowed is False
        assert "RPM" in result.message

    @pytest.mark.asyncio
    async def test_daily_cost_budget(self, quota_manager):
        cfg = QuotaConfig(rpm=1000, daily_budget_usd=0.001)
        quota_manager.set_quota("t1", cfg)
        result = await quota_manager.check_and_consume(
            tenant_id="t1", model="gpt-4o", provider="openai",
            prompt_tokens=1000, completion_tokens=500,
        )
        assert result.allowed is False
        assert "cost" in result.message.lower()

    def test_fallback_models(self, quota_manager):
        chain = quota_manager.get_fallback_models("gpt-4o", "openai")
        assert chain == ["gpt-4o-mini", "gpt-3.5-turbo"]
        next_m = quota_manager.get_next_fallback("gpt-4o", "openai")
        assert next_m == "gpt-4o-mini"


class TestConcurrentAccess:
    @pytest.mark.asyncio
    async def test_concurrent_rpm(self, quota_manager, tenant_config):
        quota_manager.set_quota("tenant-1", tenant_config)

        async def req(i):
            return await quota_manager.check_and_consume(
                tenant_id="tenant-1", model="gpt-4o-mini", provider="openai",
                prompt_tokens=10, completion_tokens=10,
            )

        results = await asyncio.gather(*[req(i) for i in range(20)])
        allowed = sum(1 for r in results if r.allowed)
        assert allowed <= 10
