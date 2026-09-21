"""DT-Lite AI Service - 智能层 (Model Gateway & API)

FastAPI application with lifespan-based dependency injection.
R2: JWT auth + permission on all endpoints.
R3: ModelGateway is the sole entry point for model calls.
R5: Every call records token usage and cost.
R6: Async with timeout + circuit breaker.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from services.ai.api.deps import (
    set_gateway,
    set_quota_manager,
    set_health_checker,
    set_cost_tracker,
    set_audit_logger,
)
from services.ai.model.gateway import ModelGateway
from services.ai.model.health import HealthChecker
from services.ai.model.quota import TenantQuotaManager
from services.ai.model.cost import CostTracker
from services.ai.audit.logger import AuditLogger

from services.ai.api.routes import chat, agent, rag, workflow, admin
from services.ai.api.websocket import router as ws_router
from services.core.config import settings

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Initialize shared services on startup, clean up on shutdown."""
    logger.info("AI service starting up, registering model gateway...")
    gw = await ModelGateway.create()
    set_gateway(gw)
    set_quota_manager(gw._quota)
    set_health_checker(gw._health)
    set_cost_tracker(gw._cost)
    set_audit_logger(gw._audit)
    logger.info("AI service ready")
    yield
    # Shutdown cleanup
    await gw._quota.close()
    await gw._cost.close()
    logger.info("AI service shut down")


app = FastAPI(
    title="DT-Lite AI Service",
    description="Model Gateway & API layer for DT-Lite v4",
    version="4.0.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ------------------------------------------------------------------ routes
app.include_router(chat.router, prefix="/api/v1/ai")
app.include_router(agent.router, prefix="/api/v1/ai")
app.include_router(rag.router, prefix="/api/v1/ai")
app.include_router(workflow.router, prefix="/api/v1/ai")
app.include_router(admin.router, prefix="/api/v1/ai")
app.include_router(ws_router, prefix="/api/v1/ai")


# ------------------------------------------------------------------ health
@app.get("/health")
async def health_check():
    from services.ai.api.deps import get_health_checker
    hc = get_health_checker()
    providers = {}
    for pname in ["openai", "anthropic", "ollama", "vllm"]:
        providers[pname] = hc.health_check(pname)
    return {
        "status": "ok",
        "version": "4.0.0",
        "providers": providers,
    }


@app.get("/api/v1/ai/status")
async def status():
    from services.ai.api.deps import get_gateway
    gw = get_gateway()
    return await gw.get_status()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "services.ai.main:app",
        host="0.0.0.0",
        port=8006,
        reload=settings.DEBUG,
        log_level="info",
    )
