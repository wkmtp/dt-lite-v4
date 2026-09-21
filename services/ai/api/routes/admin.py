"""Admin endpoints for model configuration and tenant quotas.

R2: JWT + admin permission required.
"""

from __future__ import annotations

import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends

from services.ai.api.schemas import ModelConfig, QuotaConfig
from services.ai.api.deps import get_current_tenant, require_admin_permission, get_gateway, get_health_checker, get_quota_manager, get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/admin", tags=["ai-admin"])


# ---------------------------------------------------------------- model mgmt
@router.get("/models")
async def list_models(
    _tenant: UUID = Depends(get_current_tenant),
    _user = Depends(require_admin_permission("ai:admin")),
):
    """List all registered model slots with health status."""
    gw = get_gateway()
    hc = get_health_checker()
    status_list = await gw.get_status()
    for slot in status_list.get("slots", []):
        slot["health"] = hc.get_circuit(slot["provider"]).value
    return {"success": True, "data": status_list}


@router.post("/models/{provider}/{model}/toggle")
async def toggle_model(
    provider: str,
    model: str,
    body: dict,
    _tenant: UUID = Depends(get_current_tenant),
    _user = Depends(require_admin_permission("ai:admin")),
):
    enabled = body.get("enabled", True)
    gw = get_gateway()
    await gw.toggle_provider(provider, enabled)
    return {"success": True, "data": {"provider": provider, "model": model, "enabled": enabled}}


# ---------------------------------------------------------------- quota mgmt
@router.get("/quotas")
async def list_quotas(
    _tenant: UUID = Depends(get_current_tenant),
    _user = Depends(require_admin_permission("ai:admin")),
):
    """List all tenant quota configurations (admin view)."""
    qm = get_quota_manager()
    # Return defaults since runtime configs are in-memory
    return {"success": True, "data": {"configs": {k: v.model_dump() for k, v in qm._configs.items()}}}


@router.put("/quotas/{tenant_id}")
async def update_quota(
    tenant_id: str,
    body: QuotaConfig,
    _current: UUID = Depends(get_current_tenant),
    _user = Depends(require_admin_permission("ai:admin")),
):
    """Update quota for a specific tenant."""
    qm = get_quota_manager()
    qm.set_quota(tenant_id, body)
    return {"success": True, "data": body.model_dump()}


@router.get("/quotas/{tenant_id}/usage")
async def get_quota_usage(
    tenant_id: str,
    _current: UUID = Depends(get_current_tenant),
    _user = Depends(require_admin_permission("ai:admin")),
):
    """Get current quota usage for a tenant."""
    from services.ai.model.cost import CostTracker
    ct = CostTracker()
    await ct.connect()
    today = await ct.get_daily_cost(tenant_id)
    await ct.close()
    return {"success": True, "data": {"tenant_id": tenant_id, "daily_cost_usd": today}}
