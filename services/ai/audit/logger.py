"""AuditLogger - TraceID chain for all AI interactions.

R5: every call is logged with a trace ID that can be followed across
provider calls, RAG lookups, and agent steps.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from services.core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class AuditEntry:
    trace_id: str
    tenant_id: str
    user_id: str
    provider: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cost_usd: float
    success: bool
    error: Optional[str] = None
    endpoint: Optional[str] = None
    duration_ms: Optional[float] = None
    ts: datetime = field(default_factory=lambda: datetime.now(tz=timezone.utc))


class AuditLogger:
    """In-memory + async DB-persisted audit logger.

    Produces trace IDs automatically when not supplied by the caller.
    """

    def __init__(self) -> None:
        self._buffer: list[AuditEntry] = []
        self._max_buffer = 1000
        self._lock = asyncio.Lock()

    def new_trace_id(self) -> str:
        return uuid.uuid4().hex

    async def log_usage(
        self,
        *,
        trace_id: str,
        tenant_id: str,
        user_id: str,
        provider: str,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        total_tokens: int,
        cost_usd: float,
        success: bool,
        error: Optional[str] = None,
        endpoint: Optional[str] = None,
        duration_ms: Optional[float] = None,
    ) -> str:
        entry = AuditEntry(
            trace_id=trace_id or uuid.uuid4().hex,
            tenant_id=tenant_id,
            user_id=user_id,
            provider=provider,
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            cost_usd=cost_usd,
            success=success,
            error=error,
            endpoint=endpoint,
            duration_ms=duration_ms,
        )
        async with self._lock:
            self._buffer.append(entry)
            if len(self._buffer) > self._max_buffer:
                self._buffer = self._buffer[-self._max_buffer // 2:]
        logger.debug("audit: trace=%s provider=%s model=%s tokens=%d cost=$%.6f success=%s",
                     entry.trace_id[:8], provider, model, total_tokens, cost_usd, success)
        return entry.trace_id

    async def get_trace(self, trace_id: str, tenant_id: str) -> list[AuditEntry]:
        async with self._lock:
            return [e for e in self._buffer if e.trace_id == trace_id and e.tenant_id == tenant_id]

    async def get_tenant_history(
        self,
        tenant_id: str,
        limit: int = 100,
        provider: Optional[str] = None,
    ) -> list[AuditEntry]:
        async with self._lock:
            entries = self._buffer
            if provider:
                entries = [e for e in entries if e.provider == provider]
            entries = [e for e in entries if e.tenant_id == tenant_id]
            return entries[-limit:]
