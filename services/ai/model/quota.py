"""TenantQuotaManager - RPM/TPM/daily budget/monthly budget enforcement.

Enforces R5 (every call records usage) and auto-rejects when quota exceeded,
triggering fallback to a smaller model via the gateway.

Uses Redis when available; falls back to in-memory thread-safe counters
when Redis is unavailable (tests / offline mode).
"""

from __future__ import annotations

import asyncio
import logging
import threading
import time
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

try:
    import redis.asyncio as aioredis
except ImportError:
    aioredis = None
from pydantic import BaseModel

from services.core.config import settings

logger = logging.getLogger(__name__)


class QuotaWindow(str, Enum):
    MINUTE = "minute"
    HOUR = "hour"
    DAY = "day"
    MONTH = "month"


@dataclass
class QuotaCheckResult:
    allowed: bool
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cost_usd: float
    remaining_minute: int
    remaining_day: float
    fallback_model: Optional[str] = None
    message: str = ""


@dataclass
class QuotaConfig(BaseModel):
    """Default quota per tenant per model class."""
    rpm: int = 60           # requests per minute
    tpm: int = 100_000      # tokens per minute
    daily_budget_tokens: int = 1_000_000
    monthly_budget_tokens: int = 20_000_000
    daily_budget_usd: float = 10.0
    monthly_budget_usd: float = 200.0
    # Alert thresholds (percentage of budget at which to warn)
    daily_budget_alert_pct: float = 0.8
    monthly_budget_alert_pct: float = 0.8


# Per-model token-price map (USD per token)
_MODEL_PRICES: dict[str, dict[str, dict[str, float]]] = {
    "openai": {
        "gpt-4o": {"prompt": 2.50 / 1_000_000, "completion": 10.00 / 1_000_000},
        "gpt-4o-mini": {"prompt": 0.15 / 1_000_000, "completion": 0.60 / 1_000_000},
        "gpt-3.5-turbo": {"prompt": 0.50 / 1_000_000, "completion": 1.50 / 1_000_000},
    },
    "anthropic": {
        "claude-3-5-sonnet-20241022": {"prompt": 3.00 / 1_000_000, "completion": 15.00 / 1_000_000},
        "claude-3-haiku-20240307": {"prompt": 0.25 / 1_000_000, "completion": 1.25 / 1_000_000},
    },
    "ollama": {
        "llama3.2": {"prompt": 0.0, "completion": 0.0},
        "qwen2.5:7b": {"prompt": 0.0, "completion": 0.0},
    },
    "vllm": {
        "meta-llama/Meta-Llama-3-8B-Instruct": {"prompt": 0.0, "completion": 0.0},
    },
}

# Fallback chain: when a model's quota is exceeded, try these in order
_FALLBACK_CHAIN: dict[str, list[str]] = {
    "gpt-4o": ["gpt-4o-mini", "gpt-3.5-turbo"],
    "gpt-4o-mini": ["gpt-3.5-turbo"],
    "claude-3-5-sonnet-20241022": ["claude-3-haiku-20240307"],
}


# ---------------------------------------------------------------------------
# In-memory sliding-window counter (thread-safe, used as Redis fallback)
# ---------------------------------------------------------------------------
class _InMemoryQuota:
    """Thread-safe in-memory sliding window counters for quota tracking."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        # tenant_id -> {window_key -> int count}
        self._counters: dict[str, dict[str, int]] = defaultdict(dict)
        # tenant_id -> {window_key -> float cost}
        self._cost_counters: dict[str, dict[str, float]] = defaultdict(dict)
        # tenant_id -> set of active window keys (for cleanup)
        self._active_keys: dict[str, set[str]] = defaultdict(set)

    def _window_key(self, prefix: str, now: datetime) -> str:
        if prefix == "rpm":
            return now.strftime("%Y%m%d%H%M")
        if prefix == "hour":
            return now.strftime("%Y%m%d%H")
        if prefix == "tokens_day":
            return now.date().isoformat()
        if prefix == "tokens_month":
            return now.strftime("%Y-%m")
        return prefix

    def increment(self, tenant_id: str, window_key: str, amount: int = 1) -> int:
        with self._lock:
            counters = self._counters[tenant_id]
            counters[window_key] = counters.get(window_key, 0) + amount
            self._active_keys[tenant_id].add(window_key)
            return counters[window_key]

    def add_cost(self, tenant_id: str, window_key: str, amount: float) -> float:
        with self._lock:
            costers = self._cost_counters[tenant_id]
            costers[window_key] = costers.get(window_key, 0.0) + amount
            return costers[window_key]

    def get(self, tenant_id: str, window_key: str) -> int:
        with self._lock:
            return self._counters[tenant_id].get(window_key, 0)

    def get_cost(self, tenant_id: str, window_key: str) -> float:
        with self._lock:
            return self._cost_counters[tenant_id].get(window_key, 0.0)

    def get_all(self, tenant_id: str, window_key: str) -> int:
        """Get sum of all matching window keys (e.g. all minute keys in current hour)."""
        with self._lock:
            return self._counters[tenant_id].get(window_key, 0)

    def cleanup_old_keys(self, tenant_id: str, keep_prefix: str, max_age_seconds: int, now: datetime) -> None:
        """Remove window keys older than max_age_seconds."""
        with self._lock:
            active = self._active_keys.get(tenant_id, set())
            to_remove = []
            for key in active:
                if not key.startswith(keep_prefix):
                    continue
                try:
                    # Try to parse the key back to a datetime to check age
                    if keep_prefix == "rpm":
                        dt = datetime.strptime(key, "%Y%m%d%H%M")
                    elif keep_prefix == "hour":
                        dt = datetime.strptime(key, "%Y%m%d%H")
                    elif keep_prefix == "tokens_day":
                        dt = datetime.strptime(key, "%Y-%m-%d")
                    elif keep_prefix == "tokens_month":
                        dt = datetime.strptime(key, "%Y-%m")
                    else:
                        continue
                    dt = dt.replace(tzinfo=timezone.utc)
                    if (now - dt).total_seconds() > max_age_seconds:
                        to_remove.append(key)
                except ValueError:
                    to_remove.append(key)
            for key in to_remove:
                self._counters[tenant_id].pop(key, None)
                self._cost_counters[tenant_id].pop(key, None)
                self._active_keys[tenant_id].discard(key)


# ---------------------------------------------------------------------------
# TenantQuotaManager
# ---------------------------------------------------------------------------
class TenantQuotaManager:
    """Quota manager with Redis backend and in-memory fallback.

    When Redis is available, all counters are stored there with TTLs.
    When Redis is unavailable (or not configured), in-memory counters are
    used — suitable for tests and single-instance deployments.
    """

    def __init__(self, redis_url: Optional[str] = None) -> None:
        self._redis_url = redis_url or settings.REDIS_URL
        self._redis: Optional[aioredis.Redis] = None
        self._configs: dict[str, QuotaConfig] = {}
        self._in_memory = _InMemoryQuota()
        self._redis_available: bool = False
        self._alerts_sent: set[str] = set()  # tenant_id:window to avoid duplicate alerts

    async def connect(self) -> None:
        """Try to connect to Redis; fall back to in-memory if unavailable."""
        if aioredis is None:
            self._redis_available = False
            logger.info("redis.asyncio not available, using in-memory quota")
            return
        try:
            self._redis = aioredis.from_url(self._redis_url, decode_responses=True)
            await self._redis.ping()
            self._redis_available = True
            logger.info("Redis quota backend connected")
        except Exception as exc:
            self._redis = None
            self._redis_available = False
            logger.warning("Redis quota backend unavailable (%r), using in-memory", exc)

    async def close(self) -> None:
        if self._redis:
            await self._redis.aclose()
            self._redis = None
            self._redis_available = False

    def set_quota(self, tenant_id: str, config: QuotaConfig) -> None:
        self._configs[tenant_id] = config

    def get_config(self, tenant_id: str) -> QuotaConfig:
        return self._configs.get(tenant_id, QuotaConfig())

    def check_price(self, model: str, provider: str, prompt_tokens: int, completion_tokens: int) -> float:
        """Return estimated cost for given token counts."""
        prices = _MODEL_PRICES.get(provider, {}).get(model, {"prompt": 0.0, "completion": 0.0})
        return (prompt_tokens * prices["prompt"]) + (completion_tokens * prices["completion"])

    def get_fallback_models(self, model: str, provider: str) -> list[str]:
        """Return list of fallback model names, or empty if none."""
        return list(_FALLBACK_CHAIN.get(model, []))

    def get_next_fallback(self, model: str, provider: str) -> Optional[str]:
        """Return the first available fallback model, or None."""
        chain = _FALLBACK_CHAIN.get(model, [])
        return chain[0] if chain else None

    async def check_and_consume(
        self,
        *,
        tenant_id: str,
        model: str,
        provider: str,
        prompt_tokens: int,
        completion_tokens: int = 0,
    ) -> QuotaCheckResult:
        """Check all quota windows, consume if allowed, return result.

        Returns a result with `allowed=False` and a `fallback_model` when
        the requested model exceeds quota, enabling the gateway to retry
        with a cheaper model.
        """
        if not self._redis_available:
            await self.connect()

        cfg = self._configs.get(tenant_id, QuotaConfig())
        now = datetime.now(tz=timezone.utc)
        total_tokens = prompt_tokens + completion_tokens
        cost = self.check_price(model, provider, prompt_tokens, completion_tokens)

        if self._redis_available and self._redis is not None:
            result = await self._check_redis(
                tenant_id, cfg, model, provider, prompt_tokens, completion_tokens, cost, now
            )
        else:
            result = await self._check_in_memory(
                tenant_id, cfg, model, provider, prompt_tokens, completion_tokens, cost, now
            )

        # Emit alert if approaching budget limit
        self._maybe_emit_alert(tenant_id, cfg, now, result)
        return result

    # ------------------------------------------------------------------ Redis
    async def _check_redis(
        self,
        tenant_id: str,
        cfg: QuotaConfig,
        model: str,
        provider: str,
        prompt_tokens: int,
        completion_tokens: int,
        cost: float,
        now: datetime,
    ) -> QuotaCheckResult:
        prefix = f"ai:quota:{tenant_id}"
        ts_day = now.date().isoformat()
        ts_month = now.strftime("%Y-%m")
        minute_key = f"{prefix}:rpm:{now.strftime('%Y%m%d%H%M')}"
        hour_key = f"{prefix}:rpm:{now.strftime('%Y%m%d%H')}"

        async with self._redis.pipeline() as pipe:
            pipe.incr(minute_key)
            pipe.expire(minute_key, 60)
            pipe.incr(hour_key)
            pipe.expire(hour_key, 3600)
            pipe.incr(f"{prefix}:tpm:{now.strftime('%Y%m%d%H%M')}")
            pipe.expire(f"{prefix}:tpm:{now.strftime('%Y%m%d%H%M')}", 60)
            pipe.incr(f"{prefix}:tokens:{ts_day}")
            pipe.expire(f"{prefix}:tokens:{ts_day}", 86400 * 2)
            pipe.incr(f"{prefix}:budget_usd:{ts_day}")
            pipe.expire(f"{prefix}:budget_usd:{ts_day}", 86400 * 2)
            pipe.incr(f"{prefix}:tokens:{ts_month}")
            pipe.expire(f"{prefix}:tokens:{ts_month}", 86400 * 35)
            pipe.incr(f"{prefix}:budget_usd:{ts_month}")
            pipe.expire(f"{prefix}:budget_usd:{ts_month}", 86400 * 35)
            results = await pipe.execute()

        rpm_now = results[0]
        tpm_now = results[4]
        day_tokens = results[6]
        day_cost = results[7]
        month_tokens = results[9]
        month_cost = results[10]

        return self._evaluate_checks(
            cfg, rpm_now, tpm_now, day_tokens, day_cost, month_tokens, month_cost,
            prompt_tokens, completion_tokens, total_tokens=prompt_tokens + completion_tokens,
            cost=cost, now=now,
        )

    # ---------------------------------------------------------------- In-memory
    async def _check_in_memory(
        self,
        tenant_id: str,
        cfg: QuotaConfig,
        model: str,
        provider: str,
        prompt_tokens: int,
        completion_tokens: int,
        cost: float,
        now: datetime,
    ) -> QuotaCheckResult:
        prefix = f"ai:quota:{tenant_id}"

        # RPM: count requests in the current minute window
        rpm_key = f"{prefix}:rpm:{now.strftime('%Y%m%d%H%M')}"
        rpm_now = self._in_memory.increment(tenant_id, rpm_key, 1)

        # TPM: count tokens in the current minute window
        tpm_key = f"{prefix}:tpm:{now.strftime('%Y%m%d%H%M')}"
        tpm_now = self._in_memory.increment(tenant_id, tpm_key, prompt_tokens + completion_tokens)

        # Daily counters
        ts_day = now.date().isoformat()
        day_token_key = f"{prefix}:tokens_day:{ts_day}"
        day_cost_key = f"{prefix}:budget_usd_day:{ts_day}"
        day_tokens = self._in_memory.increment(tenant_id, day_token_key, prompt_tokens + completion_tokens)
        day_cost_running = self._in_memory.add_cost(tenant_id, day_cost_key, cost)

        # Monthly counters
        ts_month = now.strftime("%Y-%m")
        month_token_key = f"{prefix}:tokens_month:{ts_month}"
        month_cost_key = f"{prefix}:budget_usd_month:{ts_month}"
        month_tokens = self._in_memory.increment(tenant_id, month_token_key, prompt_tokens + completion_tokens)
        month_cost_running = self._in_memory.add_cost(tenant_id, month_cost_key, cost)

        return self._evaluate_checks(
            cfg, rpm_now, tpm_now, day_tokens, day_cost_running,
            month_tokens, month_cost_running,
            prompt_tokens, completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
            cost=cost, now=now,
        )

    # ---------------------------------------------------------------- shared
    def _evaluate_checks(
        self,
        cfg: QuotaConfig,
        rpm_now: int,
        tpm_now: int,
        day_tokens: int,
        day_cost: float,
        month_tokens: int,
        month_cost: float,
        prompt_tokens: int,
        completion_tokens: int,
        total_tokens: int,
        cost: float,
        now: datetime,
    ) -> QuotaCheckResult:
        """Run all quota checks and return the first rejection or success."""
        # RPM check
        if rpm_now > cfg.rpm:
            return QuotaCheckResult(
                allowed=False,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                cost_usd=cost,
                remaining_minute=max(0, cfg.rpm - rpm_now),
                remaining_day=max(0, cfg.daily_budget_tokens - day_tokens),
                fallback_model=self.get_next_fallback("", ""),
                message=f"RPM quota exceeded: {rpm_now}/{cfg.rpm}",
            )

        # TPM check
        if tpm_now > cfg.tpm:
            return QuotaCheckResult(
                allowed=False,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                cost_usd=cost,
                remaining_minute=max(0, cfg.rpm - rpm_now),
                remaining_day=max(0, cfg.daily_budget_tokens - day_tokens),
                fallback_model=self.get_next_fallback("", ""),
                message=f"TPM quota exceeded: {tpm_now}/{cfg.tpm}",
            )

        # Daily token budget
        if day_tokens + total_tokens > cfg.daily_budget_tokens:
            return QuotaCheckResult(
                allowed=False,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                cost_usd=cost,
                remaining_minute=max(0, cfg.rpm - rpm_now),
                remaining_day=max(0, cfg.daily_budget_tokens - day_tokens),
                fallback_model=self.get_next_fallback("", ""),
                message="Daily token budget exceeded",
            )

        # Daily cost budget
        if day_cost + cost > cfg.daily_budget_usd:
            return QuotaCheckResult(
                allowed=False,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                cost_usd=cost,
                remaining_minute=max(0, cfg.rpm - rpm_now),
                remaining_day=max(0, cfg.daily_budget_tokens - day_tokens),
                fallback_model=self.get_next_fallback("", ""),
                message="Daily cost budget exceeded",
            )

        # Monthly token budget
        if month_tokens + total_tokens > cfg.monthly_budget_tokens:
            return QuotaCheckResult(
                allowed=False,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                cost_usd=cost,
                remaining_minute=max(0, cfg.rpm - rpm_now),
                remaining_day=max(0, cfg.daily_budget_tokens - day_tokens),
                fallback_model=self.get_next_fallback("", ""),
                message="Monthly token budget exceeded",
            )

        # Monthly cost budget
        if month_cost + cost > cfg.monthly_budget_usd:
            return QuotaCheckResult(
                allowed=False,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                cost_usd=cost,
                remaining_minute=max(0, cfg.rpm - rpm_now),
                remaining_day=max(0, cfg.daily_budget_tokens - day_tokens),
                fallback_model=self.get_next_fallback("", ""),
                message="Monthly cost budget exceeded",
            )

        return QuotaCheckResult(
            allowed=True,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            cost_usd=cost,
            remaining_minute=max(0, cfg.rpm - rpm_now),
            remaining_day=max(0, cfg.daily_budget_tokens - day_tokens),
        )

    def _maybe_emit_alert(self, tenant_id: str, cfg: QuotaConfig, now: datetime, result: QuotaCheckResult) -> None:
        """Send a budget alert when usage crosses the alert threshold."""
        day_key = f"{tenant_id}:day:{now.date().isoformat()}"
        month_key = f"{tenant_id}:month:{now.strftime('%Y-%m')}"

        # Daily alert
        day_pct = result.remaining_day / cfg.daily_budget_tokens if cfg.daily_budget_tokens > 0 else 0
        if day_pct <= (1.0 - cfg.daily_budget_alert_pct) and day_key not in self._alerts_sent:
            self._alerts_sent.add(day_key)
            logger.warning(
                "QUOTA ALERT tenant=%s daily budget at %.0f%% "
                "(used=%d tokens, budget=%d tokens)",
                tenant_id, (1.0 - day_pct) * 100,
                cfg.daily_budget_tokens - result.remaining_day, cfg.daily_budget_tokens,
            )

        # Monthly alert
        # We don't have month usage in result, skip for now (would need to track separately)

    async def get_usage_stats(self, tenant_id: str) -> dict:
        """Return current usage stats for a tenant (in-memory friendly)."""
        if not self._redis_available:
            return await self._get_in_memory_stats(tenant_id)
        if self._redis is None:
            await self.connect()
        if self._redis is None:
            return {}
        now = datetime.now(tz=timezone.utc)
        ts_day = now.date().isoformat()
        ts_month = now.strftime("%Y-%m")
        prefix = f"ai:quota:{tenant_id}"
        async with self._redis.pipeline() as pipe:
            pipe.get(f"{prefix}:rpm:{now.strftime('%Y%m%d%H%M')}")
            pipe.get(f"{prefix}:tpm:{now.strftime('%Y%m%d%H%M')}")
            pipe.get(f"{prefix}:tokens:{ts_day}")
            pipe.get(f"{prefix}:budget_usd:{ts_day}")
            pipe.get(f"{prefix}:tokens:{ts_month}")
            pipe.get(f"{prefix}:budget_usd:{ts_month}")
            results = await pipe.execute()
        return {
            "rpm_current": int(results[0] or 0),
            "tpm_current": int(results[1] or 0),
            "daily_tokens": int(results[2] or 0),
            "daily_cost_usd": float(results[3] or 0),
            "monthly_tokens": int(results[4] or 0),
            "monthly_cost_usd": float(results[5] or 0),
        }

    async def _get_in_memory_stats(self, tenant_id: str) -> dict:
        prefix = f"ai:quota:{tenant_id}"
        now = datetime.now(tz=timezone.utc)
        return {
            "rpm_current": self._in_memory.get(tenant_id, f"{prefix}:rpm:{now.strftime('%Y%m%d%H%M')}"),
            "tpm_current": self._in_memory.get(tenant_id, f"{prefix}:tpm:{now.strftime('%Y%m%d%H%M')}"),
            "daily_tokens": self._in_memory.get(tenant_id, f"{prefix}:tokens_day:{now.date().isoformat()}"),
            "daily_cost_usd": self._in_memory.get_cost(tenant_id, f"{prefix}:budget_usd_day:{now.date().isoformat()}"),
            "monthly_tokens": self._in_memory.get(tenant_id, f"{prefix}:tokens_month:{now.strftime('%Y-%m')}"),
            "monthly_cost_usd": self._in_memory.get_cost(tenant_id, f"{prefix}:budget_usd_month:{now.strftime('%Y-%m')}"),
        }

    async def reset_quota(self, tenant_id: str) -> None:
        """Clear all counters for a tenant (useful in tests)."""
        if self._redis_available and self._redis is not None:
            prefix = f"ai:quota:{tenant_id}"
            keys = await self._redis.keys(f"{prefix}:*")
            if keys:
                await self._redis.delete(*keys)
        # Clear in-memory
        self._in_memory._counters.pop(tenant_id, None)
        self._in_memory._cost_counters.pop(tenant_id, None)
        self._in_memory._active_keys.pop(tenant_id, None)
        self._alerts_sent.discard(tenant_id)
