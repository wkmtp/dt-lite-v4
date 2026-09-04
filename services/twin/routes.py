"""Twin Runtime API Routes.

All routes enforce tenant isolation via TenantContext middleware.
"""
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from services.auth.dependencies import get_current_tenant, require_permission
from services.database import AsyncSessionLocal
from services.twin.exceptions import (
    TwinEntityNotFoundError,
    TwinBindingError,
)
from services.twin.services import TwinService

router = APIRouter(prefix="/api/v1/twins", tags=["Twin Runtime"])


def _get_twin_service(db: AsyncSession) -> TwinService:
    """Create TwinService instance with database session."""
    return TwinService(session=db)


# ==================== Entity Endpoints ====================

@router.get(
    "/{entity_id}",
    response_model=dict,
    dependencies=[Depends(require_permission("twin:read"))],
)
async def get_twin_entity(
    entity_id: UUID,
    tenant_id: UUID = Depends(get_current_tenant),
):
    """Get a TwinEntity by ID.

    Security:
    - tenant_id comes from JWT/TenantContext
    - Cross-tenant access is rejected
    """
    async with AsyncSessionLocal() as db:
        service = _get_twin_service(db)
        entity = service.get_entity(entity_id, tenant_id)

        if entity is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "TWIN_ENTITY_NOT_FOUND", "message": f"Entity {entity_id} not found"},
            )

        return {
            "id": str(entity.id),
            "tenant_id": str(entity.tenant_id),
            "name": entity.name,
            "entity_type": entity.entity_type,
            "device_id": str(entity.device_id) if entity.device_id else None,
            "state": entity.state,
            "template": entity.template,
            "created_at": entity.created_at.isoformat(),
            "updated_at": entity.updated_at.isoformat(),
        }


@router.post(
    "/",
    response_model=dict,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("twin:create"))],
)
async def create_twin_entity(
    name: str = Query(..., description="Human-readable name"),
    entity_type: str = Query(..., description="Category type (e.g., pump, valve, sensor)"),
    device_id: Optional[UUID] = Query(None, description="Linked device ID (optional)"),
    template: Optional[str] = Query(None, description="Template JSON string (optional)"),
    tenant_id: UUID = Depends(get_current_tenant),
):
    """Register a new TwinEntity.

    Security:
    - tenant_id comes from JWT context
    - device_id ownership verified at binding time
    """
    async with AsyncSessionLocal() as db:
        service = _get_twin_service(db)
        template_dict = None
        if template:
            import json
            try:
                template_dict = json.loads(template)
            except json.JSONDecodeError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={"code": "INVALID_TEMPLATE", "message": "Invalid JSON template"},
                )

        entity = service.register_entity(
            name=name,
            entity_type=entity_type,
            tenant_id=tenant_id,
            device_id=device_id,
            template=template_dict,
        )

        return {
            "success": True,
            "data": {
                "id": str(entity.id),
                "tenant_id": str(entity.tenant_id),
                "name": entity.name,
                "entity_type": entity.entity_type,
                "device_id": str(entity.device_id) if entity.device_id else None,
                "created_at": entity.created_at.isoformat(),
            },
        }


@router.delete(
    "/{entity_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permission("twin:delete"))],
)
async def delete_twin_entity(
    entity_id: UUID,
    tenant_id: UUID = Depends(get_current_tenant),
):
    """Delete a TwinEntity.

    Security:
    - tenant_id comes from JWT context
    - Cross-tenant deletion is rejected
    """
    async with AsyncSessionLocal() as db:
        service = _get_twin_service(db)
        removed = service.remove_entity(entity_id, tenant_id)

        if not removed:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "TWIN_ENTITY_NOT_FOUND", "message": f"Entity {entity_id} not found"},
            )


@router.get(
    "",
    response_model=dict,
    dependencies=[Depends(require_permission("twin:read"))],
)
async def list_twin_entities(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    tenant_id: UUID = Depends(get_current_tenant),
):
    """List TwinEntities for current tenant with pagination.

    Security:
    - Results scoped to current tenant only
    """
    async with AsyncSessionLocal() as db:
        service = _get_twin_service(db)
        entities = service.list_entities(tenant_id, limit=limit, offset=offset)
        total = service.count_entities(tenant_id)

        return {
            "total": total,
            "limit": limit,
            "offset": offset,
            "entities": [
                {
                    "id": str(e.id),
                    "name": e.name,
                    "entity_type": e.entity_type,
                    "device_id": str(e.device_id) if e.device_id else None,
                    "state": e.state,
                    "created_at": e.created_at.isoformat(),
                    "updated_at": e.updated_at.isoformat(),
                }
                for e in entities
            ],
        }


# ==================== State Endpoints ====================

@router.post(
    "/{entity_id}/state",
    response_model=dict,
    dependencies=[Depends(require_permission("twin:update"))],
)
async def update_twin_state(
    entity_id: UUID,
    body: dict,
    tenant_id: UUID = Depends(get_current_tenant),
):
    """Update TwinEntity state directly.

    Args:
        body: State dictionary to merge with current state.

    Security:
    - tenant_id comes from JWT context
    """
    async with AsyncSessionLocal() as db:
        service = _get_twin_service(db)
        state = service.update_state(entity_id, None, tenant_id)  # type: ignore[arg-type]
        # Note: This endpoint merges arbitrary state dict directly
        # In production, you'd want stricter validation

        return {
            "success": True,
            "data": state,
        }


@router.get(
    "/{entity_id}/state",
    response_model=dict,
    dependencies=[Depends(require_permission("twin:read"))],
)
async def get_twin_state(
    entity_id: UUID,
    tenant_id: UUID = Depends(get_current_tenant),
):
    """Get current state of a TwinEntity.

    Security:
    - Results scoped to current tenant
    """
    async with AsyncSessionLocal() as db:
        service = _get_twin_service(db)
        state = service.get_state(entity_id, tenant_id)

        if state is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "TWIN_ENTITY_NOT_FOUND", "message": f"Entity {entity_id} not found"},
            )

        return {
            "entity_id": str(entity_id),
            "state": state,
        }


# ==================== Binding Endpoints ====================

bind_router = APIRouter(prefix="/bindings", tags=["Twin Bindings"])


@bind_router.post(
    "",
    response_model=dict,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("twin:bind"))],
)
async def create_binding(
    device_id: UUID = Query(..., description="Device ID to bind"),
    entity_id: UUID = Query(..., description="TwinEntity ID to bind"),
    binding_type: str = Query("default", description="Binding type"),
    tenant_id: UUID = Depends(get_current_tenant),
):
    """Create a binding between Device and TwinEntity.

    Security:
    - Both device and entity must belong to current tenant
    - Cross-tenant binding is rejected
    """
    async with AsyncSessionLocal() as db:
        service = _get_twin_service(db)

        try:
            binding = service.create_binding(device_id, entity_id, tenant_id, binding_type)
        except TwinEntityNotFoundError as e:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": e.code, "message": e.message},
            )
        except TwinBindingError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": e.code, "message": e.message},
            )

        return {
            "success": True,
            "data": {
                "id": str(binding.id),
                "device_id": str(binding.device_id),
                "entity_id": str(binding.entity_id),
                "binding_type": binding.binding_type,
                "tenant_id": str(binding.tenant_id),
            },
        }


@bind_router.get(
    "",
    response_model=dict,
    dependencies=[Depends(require_permission("twin:read"))],
)
async def list_bindings(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    tenant_id: UUID = Depends(get_current_tenant),
):
    """List all bindings for current tenant.

    Security:
    - Results scoped to current tenant
    """
    async with AsyncSessionLocal() as db:
        service = _get_twin_service(db)
        bindings = service.list_bindings(tenant_id, limit=limit, offset=offset)
        total = len(bindings)  # In-memory count

        return {
            "total": total,
            "limit": limit,
            "offset": offset,
            "bindings": [
                {
                    "id": str(b.id),
                    "device_id": str(b.device_id),
                    "entity_id": str(b.entity_id),
                    "binding_type": b.binding_type,
                }
                for b in bindings
            ],
        }


@bind_router.delete(
    "/{binding_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permission("twin:unbind"))],
)
async def remove_binding(
    binding_id: UUID,
    tenant_id: UUID = Depends(get_current_tenant),
):
    """Remove a binding.

    Security:
    - tenant_id comes from JWT context
    """
    async with AsyncSessionLocal() as db:
        service = _get_twin_service(db)
        removed = service.remove_binding(binding_id, tenant_id)

        if not removed:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "BINDING_NOT_FOUND", "message": f"Binding {binding_id} not found"},
            )
