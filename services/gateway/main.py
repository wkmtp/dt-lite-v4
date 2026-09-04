"""DT-Lite Gateway Service - Unified API Entry Point"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from services.core.config import settings
from services.gateway.middleware import TenantContextMiddleware

app = FastAPI(
    title="DT-Lite Gateway",
    description="DT-Lite V4.0 API Gateway - Unified Entry Point",
    version="4.0.0",
    docs_url="/api/v1/openapi.json",
    redoc_url=None,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Tenant context middleware
app.add_middleware(TenantContextMiddleware)


@app.get("/")
async def root():
    return {
        "service": "DT-Lite Gateway",
        "version": "4.0.0",
        "status": "running"
    }


@app.get("/health")
async def health_check():
    return {"status": "ok"}


@app.get("/api/v1/health")
async def api_health():
    return {
        "success": True,
        "data": {
            "service": "DT-Lite Gateway",
            "version": "4.0.0"
        }
    }


# Include v2 routers (Task 4)
from services.auth.api.routes import router as auth_router
from services.core.api.v2.routes import router as core_router
from services.identity.api.v2.routes import router as identity_router
from services.telemetry.routes import router as telemetry_router
from services.twin_graph.routes import router as twin_graph_router
from services.template.routes import router as template_router
from services.ontology.routes import router as ontology_router
from services.deployment.routes import router as deployment_router
from services.provisioning.routes import router as provisioning_router

app.include_router(auth_router)
app.include_router(core_router)
app.include_router(identity_router)
app.include_router(telemetry_router)
app.include_router(twin_graph_router)
app.include_router(template_router)
app.include_router(ontology_router)
app.include_router(deployment_router)
app.include_router(provisioning_router)


@app.on_event("startup")
async def startup():
    """Initialize database on startup"""
    from services.database import init_db
    await init_db()
    print("DT-Lite Gateway started successfully!")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
