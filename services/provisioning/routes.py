"""Provisioning API routes — FastAPI endpoints for provisioning engine."""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from services.auth.dependencies import get_current_tenant, require_permission
from services.database import AsyncSessionLocal
from services.provisioning.schemas import (
    PlanValidationResponse,
    ProvisioningExecutionResponse,
    ProvisioningPlanCreateRequest,
    ProvisioningPlanResponse,
)
from services.provisioning.services import ProvisioningService

router = APIRouter(prefix="/api/v1/provisioning", tags=["Provisioning"])


def _get_service(db: AsyncSession) -> ProvisioningService:
    return ProvisioningService(db)


@router.post(
    "/plans",
    response_model=ProvisioningPlanResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("provisioning:create"))],
)
async def create_plan(
    request: ProvisioningPlanCreateRequest,
    tenant_id: UUID = Depends(get_current_tenant),
):
    """Create a provisioning plan from a deployment instance."""
    async with AsyncSessionLocal() as db:
        service = _get_service(db)
        try:
            plan = await service.create_plan(request.deployment_instance_id, tenant_id)
        except RuntimeError as e:
            detail = {"code": "PLAN_ERROR", "message": str(e)}
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail)
        return ProvisioningPlanResponse(
            id=plan.id,
            tenant_id=plan.tenant_id,
            deployment_instance_id=plan.deployment_instance_id,
            status=plan.status,
            total_items=plan.total_items,
            completed_items=plan.completed_items,
            error_summary=plan.error_summary,
            created_at=plan.created_at.isoformat(),
            updated_at=plan.updated_at.isoformat(),
        )


@router.get(
    "/plans/{plan_id}",
    response_model=ProvisioningPlanResponse,
    dependencies=[Depends(require_permission("provisioning:read"))],
)
async def get_plan(
    plan_id: UUID,
    tenant_id: UUID = Depends(get_current_tenant),
):
    """Get provisioning plan by ID."""
    async with AsyncSessionLocal() as db:
        service = _get_service(db)
        try:
            plan = await service.get_plan(plan_id, tenant_id)
        except RuntimeError as e:
            detail = {"code": "NOT_FOUND", "message": str(e)}
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)
        return ProvisioningPlanResponse(
            id=plan.id,
            tenant_id=plan.tenant_id,
            deployment_instance_id=plan.deployment_instance_id,
            status=plan.status,
            total_items=plan.total_items,
            completed_items=plan.completed_items,
            error_summary=plan.error_summary,
            created_at=plan.created_at.isoformat(),
            updated_at=plan.updated_at.isoformat(),
        )


@router.post(
    "/plans/{plan_id}/execute",
    response_model=ProvisioningExecutionResponse,
    dependencies=[Depends(require_permission("provisioning:execute"))],
)
async def execute_plan(
    plan_id: UUID,
    tenant_id: UUID = Depends(get_current_tenant),
):
    """Execute a provisioning plan."""
    async with AsyncSessionLocal() as db:
        service = _get_service(db)
        try:
            execution = await service.execute_plan(plan_id, tenant_id)
        except RuntimeError as e:
            detail = {"code": "EXECUTION_ERROR", "message": str(e)}
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)
        return ProvisioningExecutionResponse(
            id=execution.id,
            tenant_id=execution.tenant_id,
            plan_id=execution.plan_id,
            status=execution.status,
            started_at=execution.started_at.isoformat(),
            finished_at=execution.finished_at.isoformat() if execution.finished_at else None,
            error_message=execution.error_message,
            items_completed=execution.items_completed,
            items_failed=execution.items_failed,
        )


@router.post(
    "/plans/validate",
    response_model=PlanValidationResponse,
    dependencies=[Depends(require_permission("provisioning:read"))],
)
async def validate_deployment(
    request: ProvisioningPlanCreateRequest,
    tenant_id: UUID = Depends(get_current_tenant),
):
    """Validate a deployment instance before creating a provisioning plan."""
    async with AsyncSessionLocal() as db:
        service = _get_service(db)
        result = await service.validate_deployment(request.deployment_instance_id, tenant_id)
        return result
