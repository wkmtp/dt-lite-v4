"""Template service — business logic for template operations."""
from datetime import datetime, timezone
from typing import Sequence
from uuid import UUID, uuid4

from services.template.exceptions import (
    DuplicateCodeError,
    InvalidSchemaError,
    TemplateDeletedError,
    TemplateNotFoundError,
)
from services.template.models import TwinTemplate
from services.template.repositories import TemplateRepository
from services.template.schemas import TemplateCreateRequest, TemplateUpdateRequest
from services.template.services.schema_validator import SchemaValidator


class TemplateService:
    """Service layer for TwinTemplate operations."""

    def __init__(self, repository: TemplateRepository):
        self._repo = repository

    async def create_template(
        self,
        request: TemplateCreateRequest,
        tenant_id: UUID,
    ) -> TwinTemplate:
        """Create a new template with validation."""
        # Check for duplicate code
        existing = await self._repo.get_by_code(request.code, tenant_id)
        if existing is not None:
            raise DuplicateCodeError(request.code)

        # Validate schema
        errors = SchemaValidator.validate(request.schema_definition)
        if errors:
            raise InvalidSchemaError("; ".join(errors))

        # Create template
        template = TwinTemplate(
            id=uuid4(),
            tenant_id=tenant_id,
            code=request.code.lower(),
            name=request.name,
            industry=request.industry,
            version=request.version,
            description=request.description,
            schema_definition=request.schema_definition,
            status="active",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        await self._repo.create(template)
        return template

    async def get_template(self, template_id: UUID, tenant_id: UUID) -> TwinTemplate:
        """Get template by ID with tenant isolation."""
        template = await self._repo.get_by_id_for_tenant(template_id, tenant_id)

        if template is None:
            raise TemplateNotFoundError(template_id)

        if template.is_deleted:
            raise TemplateDeletedError(template_id)

        return template

    async def list_templates(
        self,
        tenant_id: UUID,
        limit: int = 100,
        offset: int = 0,
    ) -> Sequence[TwinTemplate]:
        """List active templates for tenant."""
        return await self._repo.list_active(tenant_id, limit, offset)

    async def update_template(
        self,
        template_id: UUID,
        request: TemplateUpdateRequest,
        tenant_id: UUID,
    ) -> TwinTemplate:
        """Update template fields."""
        template = await self.get_template(template_id, tenant_id)

        if request.name is not None:
            template.name = request.name

        if request.description is not None:
            template.description = request.description

        if request.schema_definition is not None:
            errors = SchemaValidator.validate(request.schema_definition)
            if errors:
                raise InvalidSchemaError("; ".join(errors))
            template.schema_definition = request.schema_definition

        if request.status is not None:
            template.status = request.status

        template.updated_at = datetime.now(timezone.utc)
        await self._repo.session.flush()
        await self._repo.session.refresh(template)

        return template

    async def delete_template(self, template_id: UUID, tenant_id: UUID) -> bool:
        """Soft delete a template."""
        template = await self.get_template(template_id, tenant_id)
        template.soft_delete()
        await self._repo.session.flush()
        return True
