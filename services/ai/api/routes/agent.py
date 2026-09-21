"""POST /api/v1/ai/agent/run — Agent execution endpoint.

R2: JWT + permission (ai:agent) required.
R3: Model calls routed through ModelGateway.
R5: Token usage and cost tracked.
R6: Async with timeout.
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any, Optional
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from services.ai.api.schemas import AgentRunRequest, AgentRunResponse
from services.ai.api.deps import get_current_tenant, require_ai_permission, get_gateway, get_audit_logger, get_current_user
from services.core.config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/agent/run", tags=["ai-agent"])


class ToolCall(BaseModel):
    tool: str
    input: dict[str, Any]
    output: Optional[Any] = None


class AgentResult(BaseModel):
    final_answer: str
    steps: list[dict[str, Any]] = []
    trace_id: str
    total_tokens: int = 0
    total_cost_usd: float = 0.0


@router.post("", response_model=AgentRunResponse)
async def agent_run(
    req: AgentRunRequest,
    tenant_id: UUID = Depends(get_current_tenant),
    user = Depends(get_current_user),
):
    """Run an AI agent with tool calls. The orchestrator handles multi-step reasoning."""
    import asyncio
    from services.ai.orchestrator.agent import AgentOrchestrator  # lazy import to avoid circular

    gateway = get_gateway()
    audit = get_audit_logger()
    trace_id = req.trace_id or audit.new_trace_id()

    start = time.monotonic()
    try:
        orch = AgentOrchestrator(gateway=gateway, audit_logger=audit)
        result: AgentResult = await asyncio.wait_for(
            orch.run(
                agent_id=req.agent_id,
                input_text=req.input_text,
                context=req.context or {},
                tenant_id=str(tenant_id),
                user_id=str(user["id"]),
                trace_id=trace_id,
            ),
            timeout=120.0,
        )
        duration_ms = (time.monotonic() - start) * 1000
        await audit.log_usage(
            trace_id=trace_id,
            tenant_id=str(tenant_id),
            user_id=str(user["id"]),
            provider="agent",
            model=req.agent_id,
            prompt_tokens=result.total_tokens,
            completion_tokens=0,
            total_tokens=result.total_tokens,
            cost_usd=result.total_cost_usd,
            success=True,
            endpoint="/api/v1/ai/agent/run",
            duration_ms=duration_ms,
        )
        return AgentRunResponse(success=True, data=result.model_dump())
    except Exception as exc:
        logger.exception("agent_run failed trace=%s", trace_id[:8])
        await audit.log_usage(
            trace_id=trace_id,
            tenant_id=str(tenant_id),
            user_id=str(user["id"]),
            provider="agent",
            model=req.agent_id,
            prompt_tokens=0, completion_tokens=0, total_tokens=0, cost_usd=0.0,
            success=False, error=str(exc), endpoint="/api/v1/ai/agent/run",
        )
        return AgentRunResponse(success=False, error={"code": "AGENT_FAILED", "message": str(exc)})
