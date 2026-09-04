"""Deployment API routes — FastAPI endpoints for deployment meta model."""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from services.auth.dependencies import get_current_tenant, require_permission
from services.database import AsyncSessionLocal
from services.deployment.exceptions import (
    DuplicateCodeError,
    InstanceNotFoundError,
    InvalidStatusTransitionError,
    ProfileNotFoundError,
)
from services.deployment.repositories.instance_repository import (
    DeploymentInstanceRepository,
)

from services.deployment.repositories.profile_repository import (
    DeploymentProfileRepository,
)
from services.deployment.schemas import (
    DeploymentInstanceCreateRequest,
    DeploymentInstanceResponse,
    DeploymentProfileCreateRequest,
    DeploymentProfileResponse,
    DeploymentValidationResponse,
)
from services.deployment.services.deployment_service import DeploymentService
from services.deployment.services.validation_service import DeploymentValidationService

router = APIRouter(prefix="/api/v1/deployment", tags=["Deployment"])


def _get_deployment_service(db: AsyncSession) -> DeploymentService:
    return DeploymentService(
        profile_repo=DeploymentProfileRepository(db),
        instance_repo=DeploymentInstanceRepository(db),
    )


def _get_validation_service(db: AsyncSession) -> DeploymentValidationService:
    return DeploymentValidationService(
        instance_repo=DeploymentInstanceRepository(db),
    )


@router.post(
    "/profiles",
    response_model=DeploymentProfileResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("deployment:create"))],
)
async def create_profile(
    request: DeploymentProfileCreateRequest,
    tenant_id: UUID = Depends(get_current_tenant),
):
    """Create a new deployment profile."""
    async with AsyncSessionLocal() as db:
        service = _get_deployment_service(db)
        try:
            profile = await service.create_profile(
                name=request.name,
                industry=request.industry,
                template_id=request.template_id,
                description=request.description,
                tenant_id=tenant_id,
            )
        except DuplicateCodeError as e:
            detail = {"code": e.code, "message": e.message}
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail)
        response = DeploymentProfileResponse(
            id=profile.id,
            tenant_id=profile.tenant_id,
            name=profile.name,
            industry=profile.industry,
            template_id=profile.template_id,
            description=profile.description,
            status=profile.status,
            instance_count=0,
            created_at=profile.created_at.isoformat(),
            updated_at=profile.updated_at.isoformat(),
        )
        return response


@router.get(
    "/profiles/{profile_id}",
    response_model=DeploymentProfileResponse,
    dependencies=[Depends(require_permission("deployment:read"))],
)
async def get_profile(
    profile_id: UUID,
    tenant_id: UUID = Depends(get_current_tenant),
):
    """Get deployment profile by ID."""
    async with AsyncSessionLocal() as db:
        service = _get_deployment_service(db)
        try:
            profile = await service.get_profile(profile_id, tenant_id)
        except ProfileNotFoundError as e:
            detail = {"code": e.code, "message": e.message}
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)
        response = DeploymentProfileResponse(
            id=profile.id,
            tenant_id=profile.tenant_id,
            name=profile.name,
            industry=profile.industry,
            template_id=profile.template_id,
            description=profile.description,
            status=profile.status,
            instance_count=0,
            created_at=profile.created_at.isoformat(),
            updated_at=profile.updated_at.isoformat(),
        )
        return response


@router.post(
    "/instances",
    response_model=DeploymentInstanceResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("deployment:create"))],
)
async def create_instance(
    request: DeploymentInstanceCreateRequest,
    tenant_id: UUID = Depends(get_current_tenant),
):
    """Create a new deployment instance."""
    async with AsyncSessionLocal() as db:
        service = _get_deployment_service(db)
        try:
            instance = await service.create_instance(request, tenant_id)
        except ProfileNotFoundError as e:
            detail = {"code": e.code, "message": e.message}
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)
        except DuplicateCodeError as e:
            detail = {"code": e.code, "message": e.message}
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail)
        response = DeploymentInstanceResponse(
            id=instance.id,
            tenant_id=instance.tenant_id,
            profile_id=instance.profile_id,
            name=instance.name,
            location=instance.location,
            status=instance.status,
            node_count=0,
            created_at=instance.created_at.isoformat(),
            updated_at=instance.updated_at.isoformat(),
        )
        return response


@router.get(
    "/instances/{instance_id}",
    response_model=DeploymentInstanceResponse,
    dependencies=[Depends(require_permission("deployment:read"))],
)
async def get_instance(
    instance_id: UUID,
    tenant_id: UUID = Depends(get_current_tenant),
):
    """Get deployment instance by ID."""
    async with AsyncSessionLocal() as db:
        service = _get_deployment_service(db)
        try:
            instance = await service.get_instance(instance_id, tenant_id)
        except InstanceNotFoundError as e:
            detail = {"code": e.code, "message": e.message}
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)
        response = DeploymentInstanceResponse(
            id=instance.id,
            tenant_id=instance.tenant_id,
            profile_id=instance.profile_id,
            name=instance.name,
            location=instance.location,
            status=instance.status,
            node_count=0,
            created_at=instance.created_at.isoformat(),
            updated_at=instance.updated_at.isoformat(),
        )
        return response


@router.post(
    "/instances/{instance_id}/validate",
    response_model=DeploymentValidationResponse,
    dependencies=[Depends(require_permission("deployment:validate"))],
)
async def validate_instance(
    instance_id: UUID,
    tenant_id: UUID = Depends(get_current_tenant),
):
    """Validate a deployment instance for zero-code readiness."""
    async with AsyncSessionLocal() as db:
        service = _get_validation_service(db)
        result = await service.validate(instance_id, tenant_id)
        return result


@router.post(
    "/instances/{instance_id}/status",
    dependencies=[Depends(require_permission("deployment:update"))],
)
async def update_instance_status(
    instance_id: UUID,
    new_status: str,
    tenant_id: UUID = Depends(get_current_tenant),
):
    """Transition deployment instance status."""
    async with AsyncSessionLocal() as db:
        service = _get_deployment_service(db)
        try:
            updated = await service.transition_instance_status(instance_id, new_status, tenant_id)
        except InstanceNotFoundError as e:
            detail = {"code": e.code, "message": e.message}
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)
        except InvalidStatusTransitionError as e:
            detail = {"code": e.code, "message": e.message}
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)
        return {"success": True, "data": {"id": updated.id, "status": updated.status}}
