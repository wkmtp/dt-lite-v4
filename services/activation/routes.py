"""Activation API routes — FastAPI endpoints for twin activation and commands."""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from services.auth.dependencies import get_current_tenant, require_permission
from services.database import AsyncSessionLocal
from services.activation.schemas import (
    TwinActivationLogResponse,
    TwinActivationStatusResponse,
    TwinCommandResponse,
)
from services.activation.services import TwinActivationService
from services.activation.command import TwinCommandService
from services.twin.registry import TwinEntityRegistry

# Shared registry instance (singleton pattern)
_registry = TwinEntityRegistry()

router = APIRouter(prefix="/api/v1/activation", tags=["Activation"])


def _get_activation_service(db: AsyncSession) -> TwinActivationService:
    return TwinActivationService(db, _registry)


def _get_command_service(db: AsyncSession) -> TwinCommandService:
    return TwinCommandService(db)


@router.post(
    "/twins/{entity_id}/activate",
    response_model=TwinActivationStatusResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("activation:activate"))],
)
async def activate_entity(
    entity_id: UUID,
    tenant_id: UUID = Depends(get_current_tenant),
):
    """Activate a PersistentTwinEntity — register in TwinEntityRegistry."""
    async with AsyncSessionLocal() as db:
        service = _get_activation_service(db)
        try:
            log = await service.activate(entity_id, tenant_id)
        except RuntimeError as e:
            detail = {"code": "ACTIVATION_ERROR", "message": str(e)}
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail)
        return TwinActivationStatusResponse(
            entity_id=log.twin_entity_id,
            tenant_id=log.tenant_id,
            state=log.state,
            binding_id=log.binding_id,
            activated_at=log.activated_at.isoformat() if log.activated_at else None,
            error_message=log.error_message,
        )


@router.post(
    "/twins/{entity_id}/deactivate",
    response_model=TwinActivationStatusResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("activation:deactivate"))],
)
async def deactivate_entity(
    entity_id: UUID,
    tenant_id: UUID = Depends(get_current_tenant),
):
    """Deactivate a PersistentTwinEntity — remove from TwinEntityRegistry."""
    async with AsyncSessionLocal() as db:
        service = _get_activation_service(db)
        try:
            log = await service.deactivate(entity_id, tenant_id)
        except RuntimeError as e:
            detail = {"code": "DEACTIVATION_ERROR", "message": str(e)}
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail)
        return TwinActivationStatusResponse(
            entity_id=log.twin_entity_id,
            tenant_id=log.tenant_id,
            state=log.state,
            binding_id=log.binding_id,
            activated_at=log.activated_at.isoformat() if log.activated_at else None,
            error_message=log.error_message,
        )


@router.get(
    "/twins/{entity_id}/status",
    response_model=TwinActivationStatusResponse,
    dependencies=[Depends(require_permission("activation:read"))],
)
async def get_entity_status(
    entity_id: UUID,
    tenant_id: UUID = Depends(get_current_tenant),
):
    """Get activation status for a twin entity."""
    async with AsyncSessionLocal() as db:
        service = _get_activation_service(db)
        log = await service.get_status(entity_id, tenant_id)
        return TwinActivationStatusResponse(
            entity_id=log.twin_entity_id,
            tenant_id=log.tenant_id,
            state=log.state,
            binding_id=log.binding_id,
            activated_at=log.activated_at.isoformat() if log.activated_at else None,
            error_message=log.error_message,
        )


@router.post(
    "/twins/{entity_id}/bind",
    response_model=TwinActivationLogResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("activation:activate"))],
)
async def bind_device(
    entity_id: UUID,
    binding_id: UUID,
    tenant_id: UUID = Depends(get_current_tenant),
):
    """Link a TwinBinding (Task 9) to the activation log."""
    async with AsyncSessionLocal() as db:
        service = _get_activation_service(db)
        try:
            log = await service.bind_device(entity_id, binding_id, tenant_id)
        except RuntimeError as e:
            detail = {"code": "BIND_ERROR", "message": str(e)}
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail)
        return TwinActivationLogResponse.model_validate(log)


@router.post(
    "/bindings/{binding_id}/commands",
    response_model=TwinCommandResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("command:create"))],
)
async def create_command(
    binding_id: UUID,
    request: dict,
    tenant_id: UUID = Depends(get_current_tenant),
):
    """Create a TwinCommand intent."""
    from services.activation.command import TwinCommandService
    async with AsyncSessionLocal() as db:
        command_service = TwinCommandService(db)
        try:
            command = await command_service.create_command(
                binding_id=binding_id,
                target_device_id=request.get("target_device_id"),
                command_type=request.get("command_type", "write"),
                payload=request.get("payload", {}),
                tenant_id=tenant_id,
            )
        except RuntimeError as e:
            detail = {"code": "COMMAND_ERROR", "message": str(e)}
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail)
        return TwinCommandResponse.model_validate(command)


@router.post(
    "/commands/{command_id}/send",
    response_model=TwinCommandResponse,
    dependencies=[Depends(require_permission("command:execute"))],
)
async def send_command(
    command_id: UUID,
    tenant_id: UUID = Depends(get_current_tenant),
):
    """Transition command from CREATED to SENT."""
    async with AsyncSessionLocal() as db:
        command_service = TwinCommandService(db)
        try:
            command = await command_service.send_command(command_id, tenant_id)
        except RuntimeError as e:
            detail = {"code": "COMMAND_SEND_ERROR", "message": str(e)}
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)
        return TwinCommandResponse.model_validate(command)


@router.get(
    "/commands/{command_id}",
    response_model=TwinCommandResponse,
    dependencies=[Depends(require_permission("command:read"))],
)
async def get_command(
    command_id: UUID,
    tenant_id: UUID = Depends(get_current_tenant),
):
    """Get a command by ID."""
    async with AsyncSessionLocal() as db:
        command_service = TwinCommandService(db)
        command = await command_service.get_command(command_id, tenant_id)
        return TwinCommandResponse.model_validate(command)
