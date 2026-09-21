"""Edge Node Main Entry Point."""
from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from services.edge.core.node import EdgeNode

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Edge node lifecycle."""
    logger.info("Starting Edge Node...")
    yield
    logger.info("Stopping Edge Node...")


app = FastAPI(
    title="DT-Lite Edge Node",
    description="Edge Computing Runtime for DT-Lite v4",
    version="4.18.0",
    lifespan=lifespan,
)


@app.get("/health")
async def health():
    return {"status": "ok", "version": "4.18.0"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("services.edge.main:app", host="0.0.0.0", port=8080)
