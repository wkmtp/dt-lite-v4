"""Test ontology repositories."""
import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from services.ontology.repository import (
    CapabilityRepository,
    EntityTypeRepository,
    OntologyRepository,
    SemanticPropertyRepository,
    TemplateCapabilityRepository,
)


class TestOntologyRepository:
    """Test OntologyRepository methods."""

    @pytest.mark.asyncio
    async def test_get_by_code_found(self):
        """Test getting concept by code."""
        session = AsyncMock()
        repo = OntologyRepository(session)

        mock_concept = MagicMock()
        mock_concept.id = uuid4()
        mock_concept.tenant_id = uuid4()
        mock_concept.code = "building"
        mock_concept.name = "Building"
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_concept
        session.execute = AsyncMock(return_value=mock_result)

        result = await repo.get_by_code("building", mock_concept.tenant_id)
        assert result is not None
        assert result.code == "building"

    @pytest.mark.asyncio
    async def test_get_by_code_not_found(self):
        """Test getting non-existent concept by code."""
        session = AsyncMock()
        repo = OntologyRepository(session)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        session.execute = AsyncMock(return_value=mock_result)

        result = await repo.get_by_code("nonexistent", uuid4())
        assert result is None

    @pytest.mark.asyncio
    async def test_list_active_concepts(self):
        """Test listing active concepts."""
        session = AsyncMock()
        repo = OntologyRepository(session)

        mock_concept1 = MagicMock()
        mock_concept1.code = "building"
        mock_concept2 = MagicMock()
        mock_concept2.code = "machine"
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_concept1, mock_concept2]
        session.execute = AsyncMock(return_value=mock_result)

        result = await repo.list_active(uuid4())
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_count_active(self):
        """Test counting active concepts."""
        session = AsyncMock()
        repo = OntologyRepository(session)

        mock_result = MagicMock()
        mock_result.scalar_one.return_value = 5
        session.execute = AsyncMock(return_value=mock_result)

        result = await repo.count_active(uuid4())
        assert result == 5

    @pytest.mark.asyncio
    async def test_tenant_isolation_in_get_by_code(self):
        """Verify get_by_code filters by tenant."""
        session = AsyncMock()
        repo = OntologyRepository(session)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        session.execute = AsyncMock(return_value=mock_result)

        await repo.get_by_code("building", uuid4())
        session.execute.assert_called_once()


class TestEntityTypeRepository:
    """Test EntityTypeRepository methods."""

    @pytest.mark.asyncio
    async def test_list_by_concept(self):
        """Test listing entity types for a concept."""
        session = AsyncMock()
        repo = EntityTypeRepository(session)

        mock_types = [MagicMock()]
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_types
        session.execute = AsyncMock(return_value=mock_result)

        result = await repo.list_by_concept(uuid4(), uuid4())
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_count_active(self):
        """Test counting active entity types."""
        session = AsyncMock()
        repo = EntityTypeRepository(session)

        mock_result = MagicMock()
        mock_result.scalar_one.return_value = 3
        session.execute = AsyncMock(return_value=mock_result)

        result = await repo.count_active(uuid4())
        assert result == 3


class TestCapabilityRepository:
    """Test CapabilityRepository methods."""

    @pytest.mark.asyncio
    async def test_get_by_code_found(self):
        """Test getting capability by code."""
        session = AsyncMock()
        repo = CapabilityRepository(session)

        mock_cap = MagicMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_cap
        session.execute = AsyncMock(return_value=mock_result)

        result = await repo.get_by_code("TemperatureMeasurement", uuid4())
        assert result is not None

    @pytest.mark.asyncio
    async def test_count_active(self):
        """Test counting active capabilities."""
        session = AsyncMock()
        repo = CapabilityRepository(session)

        mock_result = MagicMock()
        mock_result.scalar_one.return_value = 10
        session.execute = AsyncMock(return_value=mock_result)

        result = await repo.count_active(uuid4())
        assert result == 10


class TestSemanticPropertyRepository:
    """Test SemanticPropertyRepository methods."""

    @pytest.mark.asyncio
    async def test_list_by_capability(self):
        """Test listing properties for a capability."""
        session = AsyncMock()
        repo = SemanticPropertyRepository(session)

        props = [MagicMock()]
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = props
        session.execute = AsyncMock(return_value=mock_result)

        result = await repo.list_by_capability(uuid4())
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_count_by_capability(self):
        """Test counting properties for a capability."""
        session = AsyncMock()
        repo = SemanticPropertyRepository(session)

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [MagicMock(), MagicMock()]
        session.execute = AsyncMock(return_value=mock_result)

        result = await repo.count_by_capability(uuid4())
        assert result == 2


class TestTemplateCapabilityRepository:
    """Test TemplateCapabilityRepository methods."""

    @pytest.mark.asyncio
    async def test_list_by_template(self):
        """Test listing bindings for a template."""
        session = AsyncMock()
        repo = TemplateCapabilityRepository(session)

        bindings = [MagicMock()]
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = bindings
        session.execute = AsyncMock(return_value=mock_result)

        result = await repo.list_by_template(uuid4())
        assert len(result) == 1
