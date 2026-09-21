"""POST /api/v1/ai/chat — Streaming and non-streaming chat completion.

R2: JWT + permission (ai:chat) required.
R3: All calls go through ModelGateway.
R5: Token usage and cost tracked.
R6: Async with timeout + circuit breaker.
"""

from __future__ import annotations

import json
import logging
import time
from typing import AsyncIterator, Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sse_starlette.sse import EventSourceResponse
from uuid import UUID

from services.ai.api.schemas import ChatRequest, ChatResponse
from services.ai.api.deps import get_current_tenant, require_ai_permission, get_gateway, get_audit_logger, get_current_user
from services.core.config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/chat", tags=["ai-chat"])


@router.post(
    "",
    response_model=ChatResponse,
    dependencies=[Depends(require_ai_permission("ai:chat"))],
)
async def chat(
    req: ChatRequest,
    tenant_id: UUID = Depends(get_current_tenant),
    user = Depends(get_current_user),
):
    """Non-streaming chat completion."""
    gateway = get_gateway()
    audit = get_audit_logger()
    trace_id = req.trace_id or audit.new_trace_id()
    messages = [m.model_dump() for m in req.messages]

    start = time.monotonic()
    try:
        result = await asyncio.wait_for(
            gateway.chat(
                tenant_id=str(tenant_id),
                user_id=str(user["id"]),
                model=req.model,
                messages=messages,
                temperature=req.temperature,
                max_tokens=req.max_tokens,
                stream=False,
                trace_id=trace_id,
            ),
            timeout=60.0,
        )
        duration_ms = (time.monotonic() - start) * 1000
        await audit.log_usage(
            trace_id=trace_id,
            tenant_id=str(tenant_id),
            user_id=str(user["id"]),
            provider=result.get("provider", "unknown"),
            model=req.model,
            prompt_tokens=result.get("usage", {}).get("prompt_tokens", 0),
            completion_tokens=result.get("usage", {}).get("completion_tokens", 0),
            total_tokens=result.get("usage", {}).get("total_tokens", 0),
            cost_usd=result.get("usage", {}).get("cost_usd", 0.0),
            success=True,
            endpoint="/api/v1/ai/chat",
            duration_ms=duration_ms,
        )
        return ChatResponse(success=True, data=result)
    except Exception as exc:
        logger.exception("chat failed trace=%s", trace_id[:8])
        await audit.log_usage(
            trace_id=trace_id,
            tenant_id=str(tenant_id),
            user_id=str(user["id"]),
            provider="unknown",
            model=req.model,
            prompt_tokens=0,
            completion_tokens=0,
            total_tokens=0,
            cost_usd=0.0,
            success=False,
            error=str(exc),
            endpoint="/api/v1/ai/chat",
        )
        return ChatResponse(success=False, error={"code": "CHAT_FAILED", "message": str(exc)})


@router.post(
    "/stream",
    dependencies=[Depends(require_ai_permission("ai:chat"))],
)
async def chat_stream(
    req: ChatRequest,
    tenant_id: UUID = Depends(get_current_tenant),
    user = Depends(get_current_user),
):
    """Streaming chat completion via SSE."""
    import asyncio
    gateway = get_gateway()
    audit = get_audit_logger()
    trace_id = req.trace_id or audit.new_trace_id()
    messages = [m.model_dump() for m in req.messages]

    async def _stream() -> AsyncIterator[dict]:
        try:
            async for chunk in gateway.chat_stream(
                tenant_id=str(tenant_id),
                user_id=str(user["id"]),
                model=req.model,
                messages=messages,
                temperature=req.temperature,
                max_tokens=req.max_tokens,
                trace_id=trace_id,
            ):
                yield {"event": "chunk", "data": json.dumps(chunk, default=str)}
            yield {"event": "done", "data": json.dumps({"trace_id": trace_id})}
        except Exception as exc:
            logger.exception("chat_stream failed trace=%s", trace_id[:8])
            await audit.log_usage(
                trace_id=trace_id,
                tenant_id=str(tenant_id),
                user_id=str(user["id"]),
                provider="unknown",
                model=req.model,
                prompt_tokens=0, completion_tokens=0, total_tokens=0, cost_usd=0.0,
                success=False, error=str(exc), endpoint="/api/v1/ai/chat/stream",
            )
            yield {"event": "error", "data": json.dumps({"code": "STREAM_FAILED", "message": str(exc)})}

    return EventSourceResponse(_stream())
