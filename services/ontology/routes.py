"""Ontology API routes — FastAPI endpoints for semantic meta model management."""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from services.auth.dependencies import get_current_tenant, require_permission
from services.database import AsyncSessionLocal
from services.ontology.exceptions import (
    CircularReferenceError,
    ConceptNotFoundError,
    DuplicateCodeError,
    EntityTypeNotFoundError,
    InvalidSchemaError,
    ParentNotfoundError,
)
from services.ontology.models import OntologyConcept
from services.ontology.repository import (
    CapabilityRepository,
    EntityTypeRepository,
    OntologyRepository,
)
from services.ontology.schemas import (
    CapabilityCreateRequest,
    CapabilityResponse,
    ConceptCreateRequest,
    ConceptResponse,
    ConceptUpdateRequest,
    EntityTypeCreateRequest,
    EntityTypeResponse,
)
from services.ontology.services import CapabilityService, EntityTypeService, OntologyService

router = APIRouter(prefix="/api/v1/ontology", tags=["Ontology"])


def _get_ontology_service(db: AsyncSession) -> OntologyService:
    return OntologyService(OntologyRepository(db))


def _get_entity_type_service(db: AsyncSession) -> EntityTypeService:
    return EntityTypeService(EntityTypeRepository(db))


def _get_capability_service(db: AsyncSession) -> CapabilityService:
    return CapabilityService(CapabilityRepository(db))


@router.post(
    "/concepts",
    response_model=ConceptResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("ontology:create"))],
)
async def create_concept(
    request: ConceptCreateRequest,
    tenant_id: UUID = Depends(get_current_tenant),
):
    """Create a new ontology concept."""
    async with AsyncSessionLocal() as db:
        service = _get_ontology_service(db)
        try:
            concept = await service.create_concept(request, tenant_id)
        except DuplicateCodeError as e:
            detail = {"code": e.code, "message": e.message}
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail)
        except ParentNotfoundError as e:
            detail = {"code": e.code, "message": e.message}
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)
        except CircularReferenceError as e:
            detail = {"code": e.code, "message": e.message}
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)

        children_stmt = select(OntologyConcept).where(
            OntologyConcept.parent_id == concept.id,
            OntologyConcept.tenant_id == tenant_id,
            OntologyConcept.deleted_at.is_(None),
        )
        result = await db.execute(children_stmt)
        children = result.scalars().all()

        response_data = {
            "id": concept.id,
            "tenant_id": concept.tenant_id,
            "code": concept.code,
            "name": concept.name,
            "category": concept.category,
            "parent_id": concept.parent_id,
            "description": concept.description,
            "version": concept.version,
            "children_count": len(children),
            "entity_types_count": 0,
            "created_at": concept.created_at.isoformat(),
            "updated_at": concept.updated_at.isoformat(),
        }
        return ConceptResponse(**response_data)


@router.get(
    "/concepts/{concept_id}",
    response_model=ConceptResponse,
    dependencies=[Depends(require_permission("ontology:read"))],
)
async def get_concept(
    concept_id: UUID,
    tenant_id: UUID = Depends(get_current_tenant),
):
    """Get ontology concept by ID."""
    async with AsyncSessionLocal() as db:
        service = _get_ontology_service(db)
        try:
            concept = await service.get_concept(concept_id, tenant_id)
        except ConceptNotFoundError as e:
            detail = {"code": e.code, "message": e.message}
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)

        response_data = {
            "id": concept.id,
            "tenant_id": concept.tenant_id,
            "code": concept.code,
            "name": concept.name,
            "category": concept.category,
            "parent_id": concept.parent_id,
            "description": concept.description,
            "version": concept.version,
            "children_count": 0,
            "entity_types_count": 0,
            "created_at": concept.created_at.isoformat(),
            "updated_at": concept.updated_at.isoformat(),
        }
        return ConceptResponse(**response_data)


@router.put(
    "/concepts/{concept_id}",
    response_model=ConceptResponse,
    dependencies=[Depends(require_permission("ontology:update"))],
)
async def update_concept(
    concept_id: UUID,
    request: ConceptUpdateRequest,
    tenant_id: UUID = Depends(get_current_tenant),
):
    """Update ontology concept."""
    async with AsyncSessionLocal() as db:
        service = _get_ontology_service(db)
        try:
            concept = await service.update_concept(concept_id, request, tenant_id)
        except ConceptNotFoundError as e:
            detail = {"code": e.code, "message": e.message}
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)
        except ParentNotfoundError as e:
            detail = {"code": e.code, "message": e.message}
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)
        except CircularReferenceError as e:
            detail = {"code": e.code, "message": e.message}
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)

        response_data = {
            "id": concept.id,
            "tenant_id": concept.tenant_id,
            "code": concept.code,
            "name": concept.name,
            "category": concept.category,
            "parent_id": concept.parent_id,
            "description": concept.description,
            "version": concept.version,
            "children_count": 0,
            "entity_types_count": 0,
            "created_at": concept.created_at.isoformat(),
            "updated_at": concept.updated_at.isoformat(),
        }
        return ConceptResponse(**response_data)


@router.post(
    "/entity-types",
    response_model=EntityTypeResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("ontology:create"))],
)
async def create_entity_type(
    request: EntityTypeCreateRequest,
    tenant_id: UUID = Depends(get_current_tenant),
):
    """Create a new entity type definition."""
    async with AsyncSessionLocal() as db:
        service = _get_entity_type_service(db)
        try:
            entity_type = await service.create_entity_type(request, tenant_id)
        except DuplicateCodeError as e:
            detail = {"code": e.code, "message": e.message}
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail)
        except InvalidSchemaError as e:
            detail = {"code": e.code, "message": e.message}
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=detail)

        response_data = {
            "id": entity_type.id,
            "tenant_id": entity_type.tenant_id,
            "ontology_id": entity_type.ontology_id,
            "code": entity_type.code,
            "name": entity_type.name,
            "description": entity_type.description,
            "icon": entity_type.icon,
            "property_schema": entity_type.property_schema,
            "allowed_capabilities": entity_type.allowed_capabilities,
            "status": entity_type.status,
            "capabilities_count": 0,
            "created_at": entity_type.created_at.isoformat(),
            "updated_at": entity_type.updated_at.isoformat(),
        }
        return EntityTypeResponse(**response_data)


@router.get(
    "/entity-types/{entity_type_id}",
    response_model=EntityTypeResponse,
    dependencies=[Depends(require_permission("ontology:read"))],
)
async def get_entity_type(
    entity_type_id: UUID,
    tenant_id: UUID = Depends(get_current_tenant),
):
    """Get entity type by ID."""
    async with AsyncSessionLocal() as db:
        service = _get_entity_type_service(db)
        try:
            entity_type = await service.get_entity_type(entity_type_id, tenant_id)
        except EntityTypeNotFoundError as e:
            detail = {"code": e.code, "message": e.message}
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)

        response_data = {
            "id": entity_type.id,
            "tenant_id": entity_type.tenant_id,
            "ontology_id": entity_type.ontology_id,
            "code": entity_type.code,
            "name": entity_type.name,
            "description": entity_type.description,
            "icon": entity_type.icon,
            "property_schema": entity_type.property_schema,
            "allowed_capabilities": entity_type.allowed_capabilities,
            "status": entity_type.status,
            "capabilities_count": 0,
            "created_at": entity_type.created_at.isoformat(),
            "updated_at": entity_type.updated_at.isoformat(),
        }
        return EntityTypeResponse(**response_data)


@router.post(
    "/capabilities",
    response_model=CapabilityResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("ontology:create"))],
)
async def create_capability(
    request: CapabilityCreateRequest,
    tenant_id: UUID = Depends(get_current_tenant),
):
    """Create a new capability definition."""
    async with AsyncSessionLocal() as db:
        service = _get_capability_service(db)
        try:
            capability = await service.create_capability(request, tenant_id)
        except DuplicateCodeError as e:
            detail = {"code": e.code, "message": e.message}
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail)
        except InvalidSchemaError as e:
            detail = {"code": e.code, "message": e.message}
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=detail)

        response_data = {
            "id": capability.id,
            "tenant_id": capability.tenant_id,
            "code": capability.code,
            "name": capability.name,
            "description": capability.description,
            "schema_definition": capability.schema_definition,
            "version": capability.version,
            "properties_count": 0,
            "created_at": capability.created_at.isoformat(),
            "updated_at": capability.updated_at.isoformat(),
        }
        return CapabilityResponse(**response_data)


@router.get(
    "/capabilities/{capability_id}",
    response_model=CapabilityResponse,
    dependencies=[Depends(require_permission("ontology:read"))],
)
async def get_capability(
    capability_id: UUID,
    tenant_id: UUID = Depends(get_current_tenant),
):
    """Get capability by ID."""
    async with AsyncSessionLocal() as db:
        service = _get_capability_service(db)
        try:
            capability = await service.get_capability(capability_id, tenant_id)
        except ConceptNotFoundError as e:
            detail = {"code": e.code, "message": e.message}
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)

        response_data = {
            "id": capability.id,
            "tenant_id": capability.tenant_id,
            "code": capability.code,
            "name": capability.name,
            "description": capability.description,
            "schema_definition": capability.schema_definition,
            "version": capability.version,
            "properties_count": 0,
            "created_at": capability.created_at.isoformat(),
            "updated_at": capability.updated_at.isoformat(),
        }
        return CapabilityResponse(**response_data)
