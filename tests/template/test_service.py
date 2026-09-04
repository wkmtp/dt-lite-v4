"""Test template service."""
import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from services.template.exceptions import DuplicateCodeError, InvalidSchemaError
from services.template.models import TwinTemplate
from services.template.schemas import TemplateCreateRequest, TemplateUpdateRequest
from services.template.services import TemplateService


class TestTemplateService:
    """Test TemplateService business logic."""

    def setup_method(self):
        """Setup test fixtures."""
        self.session = AsyncMock()
        self.repo = MagicMock()
        self.repo.get_by_code = AsyncMock()
        self.repo.get_by_id_for_tenant = AsyncMock()
        self.repo.list_active = AsyncMock()
        self.repo.create = AsyncMock()
        self.repo.session.flush = AsyncMock()
        self.repo.session.refresh = AsyncMock()
        self.service = TemplateService(self.repo)

    @pytest.mark.asyncio
    async def test_create_template_success(self):
        """Test successful template creation."""
        self.repo.get_by_code.return_value = None

        request = TemplateCreateRequest(
            code="building.hvac.ahu",
            name="AHU Unit",
            industry="building",
            schema_definition={"properties": [{"name": "temperature", "data_type": "float"}]},
        )

        result = await self.service.create_template(request, uuid4())
        assert result is not None
        assert result.code == "building.hvac.ahu"
        self.repo.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_template_duplicate_code_rejected(self):
        """Test duplicate code is rejected."""
        existing = TwinTemplate(
            id=uuid4(),
            tenant_id=uuid4(),
            code="building.hvac.ahu",
            name="Existing",
            industry="building",
        )
        self.repo.get_by_code.return_value = existing

        request = TemplateCreateRequest(
            code="building.hvac.ahu",
            name="Duplicate",
            industry="building",
        )

        with pytest.raises(DuplicateCodeError):
            await self.service.create_template(request, uuid4())

    @pytest.mark.asyncio
    async def test_create_template_invalid_schema_rejected(self):
        """Test invalid schema is rejected."""
        self.repo.get_by_code.return_value = None

        request = TemplateCreateRequest(
            code="test.schema",
            name="Invalid Schema",
            schema_definition={"invalid": "structure"},
        )

        with pytest.raises(InvalidSchemaError):
            await self.service.create_template(request, uuid4())

    @pytest.mark.asyncio
    async def test_get_template_success(self):
        """Test getting existing template."""
        template = TwinTemplate(
            id=uuid4(),
            tenant_id=uuid4(),
            code="building.hvac.ahu",
            name="AHU Unit",
            industry="building",
        )
        self.repo.get_by_id_for_tenant.return_value = template

        result = await self.service.get_template(template.id, template.tenant_id)
        assert result.id == template.id

    @pytest.mark.asyncio
    async def test_get_template_not_found(self):
        """Test getting non-existent template."""
        self.repo.get_by_id_for_tenant.return_value = None

        with pytest.raises(Exception):  # TemplateNotFoundError
            await self.service.get_template(uuid4(), uuid4())

    @pytest.mark.asyncio
    async def test_get_template_deleted_raises_error(self):
        """Test accessing deleted template raises error."""
        from services.template.exceptions import TemplateDeletedError

        template = TwinTemplate(
            id=uuid4(),
            tenant_id=uuid4(),
            code="test.code",
            name="Deleted",
        )
        template.soft_delete()
        self.repo.get_by_id_for_tenant.return_value = template

        with pytest.raises(TemplateDeletedError):
            await self.service.get_template(template.id, template.tenant_id)

    @pytest.mark.asyncio
    async def test_list_templates(self):
        """Test listing templates."""
        templates = [
            TwinTemplate(id=uuid4(), tenant_id=uuid4(), code="a.b.c", name="A", industry="building"),
        ]
        self.repo.list_active.return_value = templates

        result = await self.service.list_templates(uuid4())
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_update_template_name(self):
        """Test updating template name."""
        template = TwinTemplate(
            id=uuid4(),
            tenant_id=uuid4(),
            code="test.code",
            name="Original",
            industry="building",
        )
        self.repo.get_by_id_for_tenant.return_value = template

        request = TemplateUpdateRequest(name="Updated Name")
        result = await self.service.update_template(template.id, request, template.tenant_id)

        assert result.name == "Updated Name"

    @pytest.mark.asyncio
    async def test_update_template_schema_validation(self):
        """Test schema validation on update."""
        template = TwinTemplate(
            id=uuid4(),
            tenant_id=uuid4(),
            code="test.code",
            name="Test",
            industry="building",
        )
        self.repo.get_by_id_for_tenant.return_value = template

        request = TemplateUpdateRequest(schema_definition={"invalid": "structure"})

        with pytest.raises(InvalidSchemaError):
            await self.service.update_template(template.id, request, template.tenant_id)

    @pytest.mark.asyncio
    async def test_delete_template_soft_deletes(self):
        """Test soft delete of template."""
        template = TwinTemplate(
            id=uuid4(),
            tenant_id=uuid4(),
            code="test.code",
            name="To Delete",
        )
        self.repo.get_by_id_for_tenant.return_value = template

        result = await self.service.delete_template(template.id, template.tenant_id)
        assert result is True
        assert template.is_deleted is True
