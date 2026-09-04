"""Template API routes — FastAPI endpoints for template management."""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from services.auth.dependencies import get_current_tenant, require_permission
from services.database import AsyncSessionLocal
from services.template.exceptions import (
    DuplicateCodeError,
    InvalidSchemaError,
    TemplateDeletedError,
    TemplateNotFoundError,
)
from services.template.repositories import TemplateRepository
from services.template.schemas import (
    TemplateCreateRequest,
    TemplateResponse,
    TemplateUpdateRequest,
)
from services.template.services import TemplateService

router = APIRouter(prefix="/api/v1/templates", tags=["Templates"])


def _get_template_service(db: AsyncSession) -> TemplateService:
    repo = TemplateRepository(db)
    return TemplateService(repo)


@router.post(
    "",
    response_model=TemplateResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("template:create"))],
)
async def create_template(
    request: TemplateCreateRequest,
    tenant_id: UUID = Depends(get_current_tenant),
):
    """Create a new industry template."""
    async with AsyncSessionLocal() as db:
        service = _get_template_service(db)
        try:
            template = await service.create_template(request, tenant_id)
        except DuplicateCodeError as e:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail={"code": e.code, "message": e.message})
        except InvalidSchemaError as e:
            detail = {"code": e.code, "message": e.message}
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=detail)

        response_data = {
            "id": template.id,
            "tenant_id": template.tenant_id,
            "code": template.code,
            "name": template.name,
            "industry": template.industry,
            "version": template.version,
            "description": template.description,
            "schema_definition": template.schema_definition,
            "status": template.status,
            "properties_count": len(template.properties) if template.properties else 0,
            "relationships_count": len(template.relationships) if template.relationships else 0,
            "created_at": template.created_at.isoformat(),
            "updated_at": template.updated_at.isoformat(),
        }
        return TemplateResponse(**response_data)


@router.get(
    "",
    response_model=list[TemplateResponse],
    dependencies=[Depends(require_permission("template:read"))],
)
async def list_templates(
    tenant_id: UUID = Depends(get_current_tenant),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
):
    """List active templates for current tenant."""
    async with AsyncSessionLocal() as db:
        service = _get_template_service(db)
        templates = await service.list_templates(tenant_id, limit, offset)
        return [
            TemplateResponse(
                id=t.id,
                tenant_id=t.tenant_id,
                code=t.code,
                name=t.name,
                industry=t.industry,
                version=t.version,
                description=t.description,
                schema_definition=t.schema_definition,
                status=t.status,
                properties_count=len(t.properties) if t.properties else 0,
                relationships_count=len(t.relationships) if t.relationships else 0,
                created_at=t.created_at.isoformat(),
                updated_at=t.updated_at.isoformat(),
            )
            for t in templates
        ]


@router.get(
    "/{template_id}",
    response_model=TemplateResponse,
    dependencies=[Depends(require_permission("template:read"))],
)
async def get_template(
    template_id: UUID,
    tenant_id: UUID = Depends(get_current_tenant),
):
    """Get template by ID."""
    async with AsyncSessionLocal() as db:
        service = _get_template_service(db)
        try:
            template = await service.get_template(template_id, tenant_id)
        except TemplateNotFoundError as e:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"code": e.code, "message": e.message})
        except TemplateDeletedError as e:
            raise HTTPException(status_code=status.HTTP_410_GONE, detail={"code": e.code, "message": e.message})

        return TemplateResponse(
            id=template.id,
            tenant_id=template.tenant_id,
            code=template.code,
            name=template.name,
            industry=template.industry,
            version=template.version,
            description=template.description,
            schema_definition=template.schema_definition,
            status=template.status,
            properties_count=len(template.properties) if template.properties else 0,
            relationships_count=len(template.relationships) if template.relationships else 0,
            created_at=template.created_at.isoformat(),
            updated_at=template.updated_at.isoformat(),
        )


@router.put(
    "/{template_id}",
    response_model=TemplateResponse,
    dependencies=[Depends(require_permission("template:update"))],
)
async def update_template(
    template_id: UUID,
    request: TemplateUpdateRequest,
    tenant_id: UUID = Depends(get_current_tenant),
):
    """Update template fields."""
    async with AsyncSessionLocal() as db:
        service = _get_template_service(db)
        try:
            template = await service.update_template(template_id, request, tenant_id)
        except TemplateNotFoundError as e:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"code": e.code, "message": e.message})
        except InvalidSchemaError as e:
            detail = {"code": e.code, "message": e.message}
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=detail)
        except TemplateDeletedError as e:
            detail = {"code": e.code, "message": e.message}
            raise HTTPException(status_code=status.HTTP_410_GONE, detail=detail)

        response_data = {
            "id": template.id,
            "tenant_id": template.tenant_id,
            "code": template.code,
            "name": template.name,
            "industry": template.industry,
            "version": template.version,
            "description": template.description,
            "schema_definition": template.schema_definition,
            "status": template.status,
            "properties_count": len(template.properties) if template.properties else 0,
            "relationships_count": len(template.relationships) if template.relationships else 0,
            "created_at": template.created_at.isoformat(),
            "updated_at": template.updated_at.isoformat(),
        }
        return TemplateResponse(**response_data)


@router.delete(
    "/{template_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permission("template:delete"))],
)
async def delete_template(
    template_id: UUID,
    tenant_id: UUID = Depends(get_current_tenant),
):
    """Soft delete a template."""
    async with AsyncSessionLocal() as db:
        service = _get_template_service(db)
        try:
            await service.delete_template(template_id, tenant_id)
        except TemplateNotFoundError as e:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"code": e.code, "message": e.message})
        except TemplateDeletedError as e:
            raise HTTPException(status_code=status.HTTP_410_GONE, detail={"code": e.code, "message": e.message})
