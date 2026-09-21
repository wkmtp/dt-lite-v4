"""CostTracker - per-request token usage and cost tracking.

Enforces R5: every call records token usage and cost for billing/analytics.
Uses in-memory storage by default (no Redis dependency required for tests).
"""

from __future__ import annotations

import asyncio
import json
import logging
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from services.core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class CostRecord:
    tenant_id: str
    user_id: str
    trace_id: str
    provider: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cost_usd: float
    ts: datetime


@dataclass
class CostAlert:
    tenant_id: str
    alert_type: str  # "daily_budget" | "monthly_budget" | "daily_cost" | "monthly_cost"
    threshold_pct: float
    current_value: float
    budget_value: float
    ts: datetime


class CostTracker:
    """In-memory cost accumulator with alert thresholds.

    Tracks per-request token usage and cost for billing and analytics.
    All data is stored in-memory (thread-safe) so tests run without Redis.
    """

    # Per-model pricing (USD per token)
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

    def __init__(self) -> None:
        self._lock = threading.Lock()
        # tenant_id -> list of CostRecord
        self._records: dict[str, list[CostRecord]] = {}
        # tenant_id -> set of alerted (alert_type:date) to avoid duplicates
        self._alerts_sent: set[str] = set()
        # Alert thresholds (percentage)
        self._daily_budget_alert_pct: float = 0.8
        self._monthly_budget_alert_pct: float = 0.8

    # ------------------------------------------------------------------ pricing
    @classmethod
    def calculate_cost(
        cls,
        *,
        model: str,
        input_tokens: int,
        output_tokens: int,
        provider: str,
    ) -> float:
        """Calculate cost for a given model/provider/token count."""
        prices = cls._MODEL_PRICES.get(provider, {}).get(model, {"prompt": 0.0, "completion": 0.0})
        cost = (input_tokens * prices["prompt"]) + (output_tokens * prices["completion"])
        return round(cost, 10)

    # ------------------------------------------------------------------ track
    async def track(
        self,
        *,
        tenant_id: str,
        user_id: str,
        trace_id: str,
        provider: str,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        total_tokens: int,
        cost_usd: float,
    ) -> CostRecord:
        """Record a cost entry and check alert thresholds."""
        record = CostRecord(
            tenant_id=tenant_id,
            user_id=user_id,
            trace_id=trace_id,
            provider=provider,
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            cost_usd=cost_usd,
            ts=datetime.now(tz=timezone.utc),
        )
        with self._lock:
            if tenant_id not in self._records:
                self._records[tenant_id] = []
            self._records[tenant_id].append(record)
            # Keep only last 10000 records per tenant to prevent unbounded growth
            if len(self._records[tenant_id]) > 10000:
                self._records[tenant_id] = self._records[tenant_id][-5000:]

        logger.debug(
            "cost tracked: tenant=%s model=%s tokens=%d cost=$%.6f",
            tenant_id, model, total_tokens, cost_usd,
        )
        return record

    # ------------------------------------------------------------------ queries
    async def get_daily_cost(self, tenant_id: str, date_str: Optional[str] = None) -> float:
        """Get total cost for a tenant on a given day."""
        day = date_str or datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")
        with self._lock:
            records = self._records.get(tenant_id, [])
        total = sum(
            r.cost_usd for r in records
            if r.ts.strftime("%Y-%m-%d") == day
        )
        return round(total, 6)

    async def get_monthly_cost(self, tenant_id: str, month_str: Optional[str] = None) -> float:
        """Get total cost for a tenant in a given month."""
        month = month_str or datetime.now(tz=timezone.utc).strftime("%Y-%m")
        with self._lock:
            records = self._records.get(tenant_id, [])
        total = sum(
            r.cost_usd for r in records
            if r.ts.strftime("%Y-%m") == month
        )
        return round(total, 6)

    async def get_daily_tokens(self, tenant_id: str, date_str: Optional[str] = None) -> int:
        """Get total tokens for a tenant on a given day."""
        day = date_str or datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")
        with self._lock:
            records = self._records.get(tenant_id, [])
        return sum(
            r.total_tokens for r in records
            if r.ts.strftime("%Y-%m-%d") == day
        )

    async def get_monthly_tokens(self, tenant_id: str, month_str: Optional[str] = None) -> int:
        """Get total tokens for a tenant in a given month."""
        month = month_str or datetime.now(tz=timezone.utc).strftime("%Y-%m")
        with self._lock:
            records = self._records.get(tenant_id, [])
        return sum(
            r.total_tokens for r in records
            if r.ts.strftime("%Y-%m") == month
        )

    async def get_tenant_history(
        self,
        tenant_id: str,
        limit: int = 100,
        provider: Optional[str] = None,
        model: Optional[str] = None,
    ) -> list[CostRecord]:
        """Get recent cost records for a tenant."""
        with self._lock:
            records = list(self._records.get(tenant_id, []))
        if provider:
            records = [r for r in records if r.provider == provider]
        if model:
            records = [r for r in records if r.model == model]
        return records[-limit:]

    async def get_all_tenants_usage(self) -> dict[str, dict]:
        """Get usage summary for all tracked tenants."""
        with self._lock:
            tenants = dict(self._records)
        result = {}
        now = datetime.now(tz=timezone.utc)
        day = now.strftime("%Y-%m-%d")
        month = now.strftime("%Y-%m")
        for tid, records in tenants.items():
            day_records = [r for r in records if r.ts.strftime("%Y-%m-%d") == day]
            month_records = [r for r in records if r.ts.strftime("%Y-%m") == month]
            result[tid] = {
                "daily_tokens": sum(r.total_tokens for r in day_records),
                "daily_cost_usd": round(sum(r.cost_usd for r in day_records), 6),
                "monthly_tokens": sum(r.total_tokens for r in month_records),
                "monthly_cost_usd": round(sum(r.cost_usd for r in month_records), 6),
                "total_records": len(records),
            }
        return result

    # ------------------------------------------------------------------ alerts
    def set_alert_thresholds(
        self,
        daily_pct: float = 0.8,
        monthly_pct: float = 0.8,
    ) -> None:
        """Configure alert thresholds (percentage of budget)."""
        self._daily_budget_alert_pct = daily_pct
        self._monthly_budget_alert_pct = monthly_pct

    def check_and_emit_alert(
        self,
        tenant_id: str,
        *,
        daily_tokens: int,
        daily_budget_tokens: int,
        monthly_tokens: int,
        monthly_budget_tokens: int,
        daily_cost: float,
        daily_budget_usd: float,
        monthly_cost: float,
        monthly_budget_usd: float,
    ) -> list[CostAlert]:
        """Check budget thresholds and emit alerts if exceeded.

        Returns list of alerts generated (may be empty).
        """
        alerts: list[CostAlert] = []
        now = datetime.now(tz=timezone.utc)
        day_key = now.strftime("%Y-%m-%d")
        month_key = now.strftime("%Y-%m")

        # Daily token budget alert
        if daily_budget_tokens > 0:
            daily_token_pct = daily_tokens / daily_budget_tokens
            alert_key = f"{tenant_id}:daily_token:{day_key}"
            if daily_token_pct >= self._daily_budget_alert_pct and alert_key not in self._alerts_sent:
                self._alerts_sent.add(alert_key)
                alerts.append(CostAlert(
                    tenant_id=tenant_id,
                    alert_type="daily_token_budget",
                    threshold_pct=self._daily_budget_alert_pct,
                    current_value=float(daily_tokens),
                    budget_value=float(daily_budget_tokens),
                    ts=now,
                ))

        # Monthly token budget alert
        if monthly_budget_tokens > 0:
            monthly_token_pct = monthly_tokens / monthly_budget_tokens
            alert_key = f"{tenant_id}:monthly_token:{month_key}"
            if monthly_token_pct >= self._monthly_budget_alert_pct and alert_key not in self._alerts_sent:
                self._alerts_sent.add(alert_key)
                alerts.append(CostAlert(
                    tenant_id=tenant_id,
                    alert_type="monthly_token_budget",
                    threshold_pct=self._monthly_budget_alert_pct,
                    current_value=float(monthly_tokens),
                    budget_value=float(monthly_budget_tokens),
                    ts=now,
                ))

        # Daily cost budget alert
        if daily_budget_usd > 0:
            daily_cost_pct = daily_cost / daily_budget_usd
            alert_key = f"{tenant_id}:daily_cost:{day_key}"
            if daily_cost_pct >= self._daily_budget_alert_pct and alert_key not in self._alerts_sent:
                self._alerts_sent.add(alert_key)
                alerts.append(CostAlert(
                    tenant_id=tenant_id,
                    alert_type="daily_cost_budget",
                    threshold_pct=self._daily_budget_alert_pct,
                    current_value=round(daily_cost, 6),
                    budget_value=daily_budget_usd,
                    ts=now,
                ))

        # Monthly cost budget alert
        if monthly_budget_usd > 0:
            monthly_cost_pct = monthly_cost / monthly_budget_usd
            alert_key = f"{tenant_id}:monthly_cost:{month_key}"
            if monthly_cost_pct >= self._monthly_budget_alert_pct and alert_key not in self._alerts_sent:
                self._alerts_sent.add(alert_key)
                alerts.append(CostAlert(
                    tenant_id=tenant_id,
                    alert_type="monthly_cost_budget",
                    threshold_pct=self._monthly_budget_alert_pct,
                    current_value=round(monthly_cost, 6),
                    budget_value=monthly_budget_usd,
                    ts=now,
                ))

        return alerts

    def reset_alerts(self, tenant_id: Optional[str] = None) -> None:
        """Clear sent alerts (useful in tests)."""
        if tenant_id is None:
            self._alerts_sent.clear()
        else:
            self._alerts_sent = {
                k for k in self._alerts_sent if not k.startswith(f"{tenant_id}:")
            }

    def reset_records(self, tenant_id: Optional[str] = None) -> None:
        """Clear cost records (useful in tests)."""
        with self._lock:
            if tenant_id is None:
                self._records.clear()
            else:
                self._records.pop(tenant_id, None)

    def reset_all(self, tenant_id: Optional[str] = None) -> None:
        """Reset records and alerts for a tenant or all tenants."""
        self.reset_records(tenant_id)
        self.reset_alerts(tenant_id)
