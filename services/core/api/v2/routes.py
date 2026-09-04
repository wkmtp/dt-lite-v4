"""Core Domain API Routes v2 - Entity, Asset, Property, Relationship.

All routes go through Service Layer → Repository Layer.
Router never touches SQLAlchemy directly.
"""
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from services.auth.dependencies import get_current_tenant, require_permission
from services.core.schemas.asset import AssetCreate, AssetListResponse, AssetResponse, AssetUpdate
from services.core.schemas.entity import (
    EntityCreate,
    EntityListResponse,
    EntityResponse,
    EntityUpdate,
)
from services.core.schemas.property import (
    PropertyListResponse,
    PropertyValueResponse,
    PropertyValueSet,
)
from services.core.schemas.relationship import (
    RelationshipCreate,
    RelationshipListResponse,
    RelationshipResponse,
)
from services.core.services.asset_service import AssetService
from services.core.services.entity_service import EntityService
from services.core.services.property_service import PropertyService
from services.core.services.relationship_service import RelationshipService
from services.core.unit_of_work import UnitOfWork
from services.database import AsyncSessionLocal
from services.exceptions.base import (
    AssetAlreadyExists,
    EntityNotFound,
    InvalidPropertyType,
    ValidationError,
)


def _not_found(resource: str, resource_id) -> dict:
    """Return a 404 detail dict."""
    return {"code": f"{resource}_NOT_FOUND", "message": f"{resource} {resource_id} not found"}

router = APIRouter(prefix="/api/v1", tags=["Core"])


# ==================== ENTITY ENDPOINTS ====================

@router.post("/entities", response_model=EntityResponse, status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(require_permission("entity:create"))])
async def create_entity(
    data: EntityCreate,
    tenant_id: UUID = Depends(get_current_tenant),
):
    """Create a new entity."""
    async with AsyncSessionLocal() as db:
        uow = UnitOfWork(db)
        service = EntityService(uow)
        try:
            entity, event = await service.create_entity(data, tenant_id)
        except (EntityNotFound, ValidationError) as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail={"code": e.code, "message": e.message})
    return entity


@router.get("/entities", response_model=EntityListResponse)
async def list_entities(
    tenant_id: UUID = Depends(get_current_tenant),
    entity_type: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
):
    """List entities with pagination."""
    async with AsyncSessionLocal() as db:
        uow = UnitOfWork(db)
        service = EntityService(uow)
        result = await service.list_entities(tenant_id, entity_type, skip, limit)
    return result


@router.get("/entities/{entity_id}", response_model=EntityResponse)
async def get_entity(
    entity_id: UUID,
    tenant_id: UUID = Depends(get_current_tenant),
):
    """Get entity by ID."""
    async with AsyncSessionLocal() as db:
        uow = UnitOfWork(db)
        service = EntityService(uow)
        entity = await service.get_entity(entity_id, tenant_id)
    if entity is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "ENTITY_NOT_FOUND",
                "message": f"Entity {entity_id} not found",
            },
        )
    return entity


@router.patch(
    "/entities/{entity_id}",
    response_model=EntityResponse,
    dependencies=[Depends(require_permission("entity:update"))],
)
async def update_entity(
    entity_id: UUID,
    data: EntityUpdate,
    tenant_id: UUID = Depends(get_current_tenant),
):
    """Update an entity."""
    async with AsyncSessionLocal() as db:
        uow = UnitOfWork(db)
        service = EntityService(uow)
        entity = await service.update_entity(entity_id, data, tenant_id)
    if entity is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "ENTITY_NOT_FOUND",
                "message": f"Entity {entity_id} not found",
            },
        )
    return entity


@router.delete(
    "/entities/{entity_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permission("entity:delete"))],
)
async def delete_entity(
    entity_id: UUID,
    tenant_id: UUID = Depends(get_current_tenant),
):
    """Soft delete an entity."""
    async with AsyncSessionLocal() as db:
        uow = UnitOfWork(db)
        service = EntityService(uow)
        deleted = await service.delete_entity(entity_id, tenant_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "ENTITY_NOT_FOUND",
                "message": f"Entity {entity_id} not found",
            },
        )


# ==================== ASSET ENDPOINTS ====================

@router.post("/assets", response_model=AssetResponse, status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(require_permission("asset:create"))])
async def create_asset(
    data: AssetCreate,
    tenant_id: UUID = Depends(get_current_tenant),
):
    """Create a new asset bound to an entity."""
    async with AsyncSessionLocal() as db:
        uow = UnitOfWork(db)
        service = AssetService(uow)
        try:
            asset, event = await service.create_asset(data, tenant_id)
        except (EntityNotFound, AssetAlreadyExists) as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail={"code": e.code, "message": e.message})
    return asset


@router.get("/assets", response_model=AssetListResponse)
async def list_assets(
    tenant_id: UUID = Depends(get_current_tenant),
    asset_class: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
):
    """List assets with pagination."""
    async with AsyncSessionLocal() as db:
        uow = UnitOfWork(db)
        service = AssetService(uow)
        result = await service.list_assets(asset_class, tenant_id, skip, limit)
    return result


@router.get("/assets/{asset_id}", response_model=AssetResponse)
async def get_asset(
    asset_id: UUID,
    tenant_id: UUID = Depends(get_current_tenant),
):
    """Get asset by ID."""
    async with AsyncSessionLocal() as db:
        uow = UnitOfWork(db)
        service = AssetService(uow)
        asset = await service.get_asset(asset_id, tenant_id)
    if asset is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=_not_found("Asset", asset_id),
        )
    return asset


@router.patch(
    "/assets/{asset_id}",
    response_model=AssetResponse,
    dependencies=[Depends(require_permission("asset:update"))],
)
async def update_asset(
    asset_id: UUID,
    data: AssetUpdate,
    tenant_id: UUID = Depends(get_current_tenant),
):
    """Update an asset."""
    async with AsyncSessionLocal() as db:
        uow = UnitOfWork(db)
        service = AssetService(uow)
        asset = await service.update_asset(asset_id, data, tenant_id)
    if asset is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=_not_found("Asset", asset_id),
        )
    return asset


@router.delete(
    "/assets/{asset_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permission("asset:delete"))],
)
async def delete_asset(
    asset_id: UUID,
    tenant_id: UUID = Depends(get_current_tenant),
):
    """Soft delete an asset."""
    async with AsyncSessionLocal() as db:
        uow = UnitOfWork(db)
        service = AssetService(uow)
        deleted = await service.delete_asset(asset_id, tenant_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=_not_found("Asset", asset_id),
        )


# ==================== PROPERTY ENDPOINTS ====================

@router.get("/property-definitions", response_model=PropertyListResponse)
async def list_property_definitions(
    tenant_id: UUID = Depends(get_current_tenant),
    entity_type: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
):
    """List property definitions."""
    async with AsyncSessionLocal() as db:
        uow = UnitOfWork(db)
        service = PropertyService(uow)
        result = await service.list_definitions(entity_type, tenant_id, skip, limit)
    return result


@router.put("/properties/{entity_id}/{definition_id}", response_model=PropertyValueResponse,
            dependencies=[Depends(require_permission("property:update"))])
async def set_property(
    entity_id: UUID,
    definition_id: UUID,
    data: PropertyValueSet,
):
    """Set a property value with type validation."""
    async with AsyncSessionLocal() as db:
        uow = UnitOfWork(db)
        service = PropertyService(uow)
        try:
            pv, event = await service.set_property(entity_id, definition_id, data.value)
        except (EntityNotFound, InvalidPropertyType) as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail={"code": e.code, "message": e.message})
    return pv


@router.get("/properties/{entity_id}", response_model=list[PropertyValueResponse])
async def get_properties(
    entity_id: UUID,
):
    """Get all properties for an entity."""
    async with AsyncSessionLocal() as db:
        uow = UnitOfWork(db)
        service = PropertyService(uow)
        pvs = await service.get_properties(entity_id)
    return pvs


# ==================== RELATIONSHIP ENDPOINTS ====================

@router.post(
    "/relationships",
    response_model=RelationshipResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("relationship:create"))],
)
async def create_relationship(
    data: RelationshipCreate,
    tenant_id: UUID = Depends(get_current_tenant),
):
    """Create a relationship between two entities."""
    async with AsyncSessionLocal() as db:
        uow = UnitOfWork(db)
        service = RelationshipService(uow)
        try:
            rel, event = await service.create_relationship(data, tenant_id)
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail={"code": "RELATIONSHIP_ERROR", "message": str(e)})
    return rel


@router.get("/relationships", response_model=RelationshipListResponse)
async def list_relationships(
    tenant_id: UUID = Depends(get_current_tenant),
    source_entity_id: Optional[UUID] = Query(None),
    target_entity_id: Optional[UUID] = Query(None),
):
    """List relationships."""
    async with AsyncSessionLocal() as db:
        uow = UnitOfWork(db)
        service = RelationshipService(uow)
        result = await service.list_relationships(tenant_id, source_entity_id, target_entity_id)
    return result


@router.delete("/relationships/{rel_id}", status_code=status.HTTP_204_NO_CONTENT,
               dependencies=[Depends(require_permission("relationship:delete"))])
async def delete_relationship(
    rel_id: UUID,
    tenant_id: UUID = Depends(get_current_tenant),
):
    """Delete a relationship."""
    async with AsyncSessionLocal() as db:
        uow = UnitOfWork(db)
        service = RelationshipService(uow)
        deleted = await service.delete_relationship(rel_id, tenant_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=_not_found("Relationship", rel_id),
        )
