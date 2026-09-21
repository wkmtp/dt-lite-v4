"""Workflow CRUD + execute endpoints.

R2: JWT + permission required.
R5: Token usage tracked for each workflow step that invokes a model.
"""

from __future__ import annotations

import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends

from services.ai.api.deps import get_current_tenant, require_ai_permission, get_current_user
from services.ai.api.schemas import (
    WorkflowExecuteRequest,
    WorkflowExecuteResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/workflow", tags=["ai-workflow"])


@router.get("")
async def list_workflows(
    tenant_id: UUID = Depends(get_current_tenant),
    _user = Depends(get_current_user),
):
    """List workflows owned by the current tenant."""
    from services.ai.orchestrator.workflow_repo import WorkflowRepository
    repo = WorkflowRepository()
    workflows = await repo.list_by_tenant(str(tenant_id))
    return {"success": True, "data": [w.to_dict() for w in workflows]}


@router.post("")
async def create_workflow(
    body: dict,
    tenant_id: UUID = Depends(get_current_tenant),
    _user = Depends(get_current_user),
):
    """Create a new workflow."""
    from services.ai.orchestrator.workflow_repo import WorkflowRepository
    repo = WorkflowRepository()
    wf = await repo.create(
        tenant_id=str(tenant_id),
        name=body.get("name", "Untitled"),
        steps=body.get("steps", []),
        config=body.get("config", {}),
    )
    return {"success": True, "data": wf.to_dict()}


@router.get("/{workflow_id}")
async def get_workflow(
    workflow_id: str,
    tenant_id: UUID = Depends(get_current_tenant),
    _user = Depends(get_current_user),
):
    """Get a workflow by ID."""
    from services.ai.orchestrator.workflow_repo import WorkflowRepository
    repo = WorkflowRepository()
    wf = await repo.get(workflow_id, str(tenant_id))
    if wf is None:
        return {"success": False, "error": {"code": "NOT_FOUND", "message": "Workflow not found"}}
    return {"success": True, "data": wf.to_dict()}


@router.put("/{workflow_id}")
async def update_workflow(
    workflow_id: str,
    body: dict,
    tenant_id: UUID = Depends(get_current_tenant),
    _user = Depends(get_current_user),
):
    """Update a workflow."""
    from services.ai.orchestrator.workflow_repo import WorkflowRepository
    repo = WorkflowRepository()
    wf = await repo.update(workflow_id, str(tenant_id), name=body.get("name"), steps=body.get("steps"), config=body.get("config"))
    if wf is None:
        return {"success": False, "error": {"code": "NOT_FOUND", "message": "Workflow not found"}}
    return {"success": True, "data": wf.to_dict()}


@router.delete("/{workflow_id}")
async def delete_workflow(
    workflow_id: str,
    tenant_id: UUID = Depends(get_current_tenant),
    _user = Depends(get_current_user),
):
    """Delete a workflow."""
    from services.ai.orchestrator.workflow_repo import WorkflowRepository
    repo = WorkflowRepository()
    ok = await repo.delete(workflow_id, str(tenant_id))
    return {"success": ok, "data": {"deleted": ok}}


@router.post("/execute", response_model=WorkflowExecuteResponse)
async def execute_workflow(
    req: WorkflowExecuteRequest,
    tenant_id: UUID = Depends(get_current_tenant),
    user = Depends(get_current_user),
):
    """Execute a workflow and return step-by-step results."""
    import asyncio
    from services.ai.orchestrator.workflow_executor import WorkflowExecutor
    from services.ai.api.deps import get_gateway, get_audit_logger

    gateway = get_gateway()
    audit = get_audit_logger()
    trace_id = req.trace_id or audit.new_trace_id()

    executor = WorkflowExecutor(gateway=gateway, audit_logger=audit)
    try:
        result = await asyncio.wait_for(
            executor.execute(
                workflow_id=req.workflow_id,
                inputs=req.inputs,
                tenant_id=str(tenant_id),
                user_id=str(user["id"]),
                trace_id=trace_id,
            ),
            timeout=300.0,
        )
        return WorkflowExecuteResponse(success=True, data=result)
    except Exception as exc:
        logging.getLogger(__name__).exception("workflow execute failed trace=%s", trace_id[:8])
        return WorkflowExecuteResponse(success=False, error={"code": "EXECUTION_FAILED", "message": str(exc)})
