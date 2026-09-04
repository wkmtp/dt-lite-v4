"""FastAPI Router for Core endpoints - Entity, Asset, Property, Relationship with Graph Query"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from services.database import get_db
from services.core.services.core_service import EntityService, AssetService, PropertyService, RelationshipService
from services.core.schemas.entity_asset import (
    EntityCreate, EntityUpdate, EntityResponse, 
    AssetCreate, AssetUpdate, AssetResponse,
    PropertyDefinitionCreate, PropertyValueUpdate, 
    RelationshipCreate, RelationshipResponse
)
from services.auth import get_current_user, get_current_tenant, require_permission
from services.identity.models.models import User

router = APIRouter(prefix="/api/v1/core", tags=["Core"])


# ========== Entity Endpoints ==========

@router.post("/entities", response_model=dict, dependencies=[Depends(require_permission("entity:create"))])
async def create_entity(
    data: EntityCreate,
    tenant_id: str = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    service = EntityService(db)
    entity = await service.create_entity(tenant_id, data.model_dump())
    return {
        "success": True,
        "data": {
            "id": str(entity.id),
            "tenant_id": str(entity.tenant_id),
            "entity_type": entity.entity_type,
            "name": entity.name,
            "status": entity.status,
            "created_at": entity.created_at.isoformat(),
        }
    }


@router.get("/entities", response_model=dict)
async def list_entities(
    tenant_id: str = Depends(get_current_tenant),
    entity_type: str = None,
    skip: int = 0,
    limit: int = 20,
    db: AsyncSession = Depends(get_db)
):
    service = EntityService(db)
    entities = await service.list_entities(tenant_id, entity_type, skip, limit)
    return {
        "success": True,
        "data": [
            {
                "id": str(e.id),
                "tenant_id": str(e.tenant_id),
                "entity_type": e.entity_type,
                "name": e.name,
                "status": e.status,
            }
            for e in entities
        ],
        "meta": {"total": len(entities)}
    }


@router.get("/entities/{entity_id}", response_model=dict)
async def get_entity(
    entity_id: str,
    tenant_id: str = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    service = EntityService(db)
    entity = await service.get_entity(entity_id, tenant_id)
    if not entity:
        raise HTTPException(status_code=404, detail={"code": "ENTITY_NOT_FOUND", "message": "Entity not found"})
    return {
        "success": True,
        "data": {
            "id": str(entity.id),
            "tenant_id": str(entity.tenant_id),
            "entity_type": entity.entity_type,
            "name": entity.name,
            "description": entity.description,
            "status": entity.status,
            "metadata": entity.extra_data,
            "created_at": entity.created_at.isoformat(),
            "updated_at": entity.updated_at.isoformat(),
        }
    }


@router.patch("/entities/{entity_id}", response_model=dict, dependencies=[Depends(require_permission("entity:update"))])
async def update_entity(
    entity_id: str,
    tenant_id: str = Depends(get_current_tenant),
    data: EntityUpdate = None,
    db: AsyncSession = Depends(get_db)
):
    service = EntityService(db)
    entity = await service.update_entity(entity_id, tenant_id, data.model_dump(exclude_none=True))
    if not entity:
        raise HTTPException(status_code=404, detail={"code": "ENTITY_NOT_FOUND", "message": "Entity not found"})
    return {
        "success": True,
        "data": {
            "id": str(entity.id),
            "name": entity.name,
            "status": entity.status,
            "updated_at": entity.updated_at.isoformat(),
        }
    }


@router.delete("/entities/{entity_id}", response_model=dict, dependencies=[Depends(require_permission("entity:delete"))])
async def delete_entity(
    entity_id: str,
    tenant_id: str = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    service = EntityService(db)
    deleted = await service.delete_entity(entity_id, tenant_id)
    if not deleted:
        raise HTTPException(status_code=404, detail={"code": "ENTITY_NOT_FOUND", "message": "Entity not found"})
    return {"success": True, "message": "Entity deleted"}


# ========== Graph Query Endpoint ==========

@router.get("/entities/{entity_id}/graph", response_model=dict)
async def get_entity_graph(
    entity_id: str,
    tenant_id: str = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    service = EntityService(db)
    graph = await service.get_entity_graph(entity_id, tenant_id)
    if "error" in graph:
        raise HTTPException(status_code=404, detail=graph["error"])
    return {
        "success": True,
        "data": graph
    }


@router.get("/entities/{entity_id}/properties", response_model=dict)
async def get_entity_properties(
    entity_id: str,
    tenant_id: str = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    """Get all property definitions and values for an entity"""
    service = EntityService(db)
    entity = await service.get_entity(entity_id, tenant_id)
    if not entity:
        raise HTTPException(status_code=404, detail={"code": "ENTITY_NOT_FOUND", "message": "Entity not found"})
    
    prop_service = PropertyService(db)
    prop_defs = await prop_service.get_property_definitions(entity.entity_type, tenant_id)
    
    properties = []
    for prop_def in prop_defs:
        value = await prop_service.get_property_value(entity_id, str(prop_def.id))
        properties.append({
            "definition_id": str(prop_def.id),
            "key": prop_def.key,
            "data_type": prop_def.data_type,
            "unit": prop_def.unit,
            "value": value,
        })
    
    return {
        "success": True,
        "data": {
            "entity_id": entity_id,
            "properties": properties,
        }
    }


@router.get("/entities/{entity_id}/relationships", response_model=dict)
async def get_entity_relationships(
    entity_id: str,
    tenant_id: str = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    service = RelationshipService(db)
    relationships = await service.list_relationships(tenant_id, entity_id)
    return {
        "success": True,
        "data": [
            {
                "id": str(r.id),
                "source_entity_id": str(r.source_entity_id),
                "target_entity_id": str(r.target_entity_id),
                "relation_type": r.relation_type,
                "created_at": r.created_at.isoformat(),
            }
            for r in relationships
        ]
    }


# ========== Asset Endpoints ==========

@router.post("/assets", response_model=dict, dependencies=[Depends(require_permission("asset:create"))])
async def create_asset(
    data: AssetCreate,
    tenant_id: str = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    service = AssetService(db)
    asset_data = data.model_dump()
    asset_data["tenant_id"] = tenant_id
    try:
        asset = await service.create_asset(asset_data)
    except ValueError as e:
        raise HTTPException(status_code=404, detail={"code": "ENTITY_NOT_FOUND", "message": str(e)})
    return {
        "success": True,
        "data": {
            "id": str(asset.id),
            "entity_id": str(asset.entity_id),
            "asset_code": asset.asset_code,
            "asset_class": asset.asset_class,
            "lifecycle_status": asset.lifecycle_status,
        }
    }


@router.get("/assets", response_model=dict)
async def list_assets(
    tenant_id: str = Depends(get_current_tenant),
    asset_class: str = None,
    skip: int = 0,
    limit: int = 20,
    db: AsyncSession = Depends(get_db)
):
    service = AssetService(db)
    assets = await service.list_assets(asset_class, skip, limit)
    return {
        "success": True,
        "data": [
            {
                "id": str(a.id),
                "entity_id": str(a.entity_id),
                "asset_code": a.asset_code,
                "asset_class": a.asset_class,
                "lifecycle_status": a.lifecycle_status,
            }
            for a in assets
        ]
    }


# ========== Property Endpoints ==========

@router.post("/properties/definitions", response_model=dict, dependencies=[Depends(require_permission("property:create"))])
async def create_property_definition(
    data: PropertyDefinitionCreate,
    tenant_id: str = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    service = PropertyService(db)
    prop_def = await service.create_property_definition({**data.model_dump(), "tenant_id": tenant_id})
    return {
        "success": True,
        "data": {
            "id": str(prop_def.id),
            "entity_type": prop_def.entity_type,
            "key": prop_def.key,
            "data_type": prop_def.data_type,
        }
    }


@router.put("/properties/values", response_model=dict, dependencies=[Depends(require_permission("property:update"))])
async def update_property_value(
    data: PropertyValueUpdate,
    db: AsyncSession = Depends(get_db)
):
    service = PropertyService(db)
    prop_value = await service.set_property_value(data.entity_id, data.property_definition_id, data.value)
    return {
        "success": True,
        "data": {
            "entity_id": str(prop_value.entity_id),
            "property_definition_id": str(prop_value.property_definition_id),
            "value": prop_value.value,
            "updated_at": prop_value.updated_at.isoformat(),
        }
    }


# ========== Relationship Endpoints ==========

@router.post("/relationships", response_model=dict, dependencies=[Depends(require_permission("relationship:create"))])
async def create_relationship(
    data: RelationshipCreate,
    tenant_id: str = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    service = RelationshipService(db)
    relationship = await service.create_relationship({**data.model_dump(), "tenant_id": tenant_id})
    return {
        "success": True,
        "data": {
            "id": str(relationship.id),
            "source_entity_id": str(relationship.source_entity_id),
            "target_entity_id": str(relationship.target_entity_id),
            "relation_type": relationship.relation_type,
        }
    }


@router.get("/relationships", response_model=dict)
async def list_relationships(
    tenant_id: str = Depends(get_current_tenant),
    entity_id: str = None,
    db: AsyncSession = Depends(get_db)
):
    service = RelationshipService(db)
    relationships = await service.list_relationships(tenant_id, entity_id)
    return {
        "success": True,
        "data": [
            {
                "id": str(r.id),
                "source_entity_id": str(r.source_entity_id),
                "target_entity_id": str(r.target_entity_id),
                "relation_type": r.relation_type,
                "created_at": r.created_at.isoformat(),
            }
            for r in relationships
        ]
    }


@router.delete("/relationships/{rel_id}", response_model=dict, dependencies=[Depends(require_permission("relationship:delete"))])
async def delete_relationship(
    rel_id: str,
    db: AsyncSession = Depends(get_db)
):
    service = RelationshipService(db)
    deleted = await service.delete_relationship(rel_id)
    if not deleted:
        raise HTTPException(status_code=404, detail={"code": "RELATIONSHIP_NOT_FOUND", "message": "Relationship not found"})
    return {"success": True, "message": "Relationship deleted"}
