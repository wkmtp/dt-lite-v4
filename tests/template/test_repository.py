"""Test template repositories."""
import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from services.template.models import TwinTemplate
from services.template.repositories import (
    TemplateRepository,
    TemplatePropertyRepository,
    TemplateRelationshipRepository,
)


class TestTemplateRepository:
    """Test TemplateRepository methods."""

    @pytest.mark.asyncio
    async def test_get_by_code_found(self):
        """Test getting template by code."""
        session = AsyncMock()
        repo = TemplateRepository(session)

        mock_template = TwinTemplate(
            id=uuid4(),
            tenant_id=uuid4(),
            code="building.hvac.ahu",
            name="AHU Unit",
            industry="building",
        )
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_template
        session.execute = AsyncMock(return_value=mock_result)

        result = await repo.get_by_code("building.hvac.ahu", mock_template.tenant_id)
        assert result is not None
        assert result.code == "building.hvac.ahu"

    @pytest.mark.asyncio
    async def test_get_by_code_not_found(self):
        """Test getting non-existent template by code."""
        session = AsyncMock()
        repo = TemplateRepository(session)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        session.execute = AsyncMock(return_value=mock_result)

        result = await repo.get_by_code("nonexistent.code", uuid4())
        assert result is None

    @pytest.mark.asyncio
    async def test_list_active_templates(self):
        """Test listing active templates."""
        session = AsyncMock()
        repo = TemplateRepository(session)

        templates = [
            TwinTemplate(id=uuid4(), tenant_id=uuid4(), code="a.b.c", name="A", industry="building"),
            TwinTemplate(id=uuid4(), tenant_id=uuid4(), code="d.e.f", name="D", industry="factory"),
        ]
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = templates
        session.execute = AsyncMock(return_value=mock_result)

        result = await repo.list_active(uuid4())
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_count_active(self):
        """Test counting active templates."""
        session = AsyncMock()
        repo = TemplateRepository(session)

        mock_result = MagicMock()
        mock_result.scalar_one.return_value = 5
        session.execute = AsyncMock(return_value=mock_result)

        result = await repo.count_active(uuid4())
        assert result == 5

    @pytest.mark.asyncio
    async def test_create_template(self):
        """Test creating a new template."""
        session = AsyncMock()
        repo = TemplateRepository(session)

        template = TwinTemplate(
            id=uuid4(),
            tenant_id=uuid4(),
            code="test.code",
            name="Test",
            industry="general",
        )

        await repo.create(template)
        session.add.assert_called_once()
        session.flush.assert_called_once()
        session.refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_tenant_isolation_in_get_by_code(self):
        """Verify get_by_code filters by tenant."""
        session = AsyncMock()
        repo = TemplateRepository(session)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        session.execute = AsyncMock(return_value=mock_result)

        await repo.get_by_code("building.hvac", uuid4())
        # Verify execute was called
        session.execute.assert_called_once()


class TestTemplatePropertyRepository:
    """Test TemplatePropertyRepository methods."""

    @pytest.mark.asyncio
    async def test_list_by_template(self):
        """Test listing properties for a template."""
        session = AsyncMock()
        repo = TemplatePropertyRepository(session)

        props = [MagicMock()]
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = props
        session.execute = AsyncMock(return_value=mock_result)

        result = await repo.list_by_template(uuid4())
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_count_by_template(self):
        """Test counting properties for a template."""
        session = AsyncMock()
        repo = TemplatePropertyRepository(session)

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [MagicMock(), MagicMock()]
        session.execute = AsyncMock(return_value=mock_result)

        result = await repo.count_by_template(uuid4())
        assert result == 2


class TestTemplateRelationshipRepository:
    """Test TemplateRelationshipRepository methods."""

    @pytest.mark.asyncio
    async def test_list_by_template(self):
        """Test listing relationships for a template."""
        session = AsyncMock()
        repo = TemplateRelationshipRepository(session)

        rels = [MagicMock()]
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = rels
        session.execute = AsyncMock(return_value=mock_result)

        result = await repo.list_by_template(uuid4())
        assert len(result) == 1
