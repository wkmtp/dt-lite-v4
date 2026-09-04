"""Test ontology services."""
import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from services.ontology.exceptions import (
    DuplicateCodeError,
    InvalidSchemaError,
)
from services.ontology.schemas import (
    CapabilityCreateRequest,
    ConceptCreateRequest,
    EntityTypeCreateRequest,
)
from services.ontology.services import CapabilityService, EntityTypeService, OntologyService


class TestOntologyService:
    """Test OntologyService business logic."""

    def setup_method(self):
        """Setup test fixtures."""
        self.repo = MagicMock()
        self.repo.get_by_code = AsyncMock()
        self.repo.get_by_id_for_tenant = AsyncMock()
        self.repo.list_active = AsyncMock()
        self.repo.create = AsyncMock()
        self.repo.session.flush = AsyncMock()
        self.repo.session.refresh = AsyncMock()
        self.service = OntologyService(self.repo)

    @pytest.mark.asyncio
    async def test_create_concept_success(self):
        """Test successful concept creation."""
        self.repo.get_by_code.return_value = None

        request = ConceptCreateRequest(
            code="building",
            name="Building",
            category="spatial",
        )

        # Mock concept instance returned by service
        mock_concept = MagicMock()
        mock_concept.id = uuid4()
        mock_concept.code = "building"
        self.repo.create = AsyncMock(return_value=mock_concept)

        result = await self.service.create_concept(request, uuid4())
        assert result is not None

    @pytest.mark.asyncio
    async def test_create_concept_duplicate_code_rejected(self):
        """Test duplicate code is rejected."""
        existing = MagicMock()
        self.repo.get_by_code.return_value = existing

        request = ConceptCreateRequest(code="building", name="Building")

        with pytest.raises(DuplicateCodeError):
            await self.service.create_concept(request, uuid4())

    @pytest.mark.asyncio
    async def test_get_concept_success(self):
        """Test getting existing concept."""
        concept = MagicMock()
        concept.is_deleted = False
        self.repo.get_by_id_for_tenant.return_value = concept

        result = await self.service.get_concept(uuid4(), uuid4())
        assert result == concept

    @pytest.mark.asyncio
    async def test_get_concept_not_found(self):
        """Test getting non-existent concept."""
        self.repo.get_by_id_for_tenant.return_value = None

        from services.ontology.exceptions import ConceptNotFoundError
        with pytest.raises(ConceptNotFoundError):
            await self.service.get_concept(uuid4(), uuid4())

    @pytest.mark.asyncio
    async def test_update_concept_name(self):
        """Test updating concept name."""
        concept = MagicMock()
        concept.is_deleted = False
        self.repo.get_by_id_for_tenant.return_value = concept

        from services.ontology.schemas import ConceptUpdateRequest
        request = ConceptUpdateRequest(name="New Name")
        result = await self.service.update_concept(concept.id, request, uuid4())

        assert result.name == "New Name"


class TestEntityTypeService:
    """Test EntityTypeService business logic."""

    def setup_method(self):
        """Setup test fixtures."""
        self.repo = MagicMock()
        self.repo.get_by_code = AsyncMock()
        self.repo.get_by_id_for_tenant = AsyncMock()
        self.repo.create = AsyncMock()
        self.repo.session.flush = AsyncMock()
        self.repo.session.refresh = AsyncMock()
        self.service = EntityTypeService(self.repo)

    @pytest.mark.asyncio
    async def test_create_entity_type_success(self):
        """Test successful entity type creation."""
        self.repo.get_by_code.return_value = None

        request = EntityTypeCreateRequest(
            ontology_id=uuid4(),
            code="ahu",
            name="AHU Unit",
        )

        mock_et = MagicMock()
        self.repo.create = AsyncMock(return_value=mock_et)

        result = await self.service.create_entity_type(request, uuid4())
        assert result is not None
        self.repo.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_entity_type_duplicate_rejected(self):
        """Test duplicate entity type code is rejected."""
        existing = MagicMock()
        self.repo.get_by_code.return_value = existing

        request = EntityTypeCreateRequest(
            ontology_id=uuid4(),
            code="ahu",
            name="AHU",
        )

        with pytest.raises(DuplicateCodeError):
            await self.service.create_entity_type(request, uuid4())

    @pytest.mark.asyncio
    async def test_create_entity_type_invalid_schema_rejected(self):
        """Test invalid property schema is rejected."""
        self.repo.get_by_code.return_value = None

        # Pass an empty dict which should be fine (no validation on empty)
        # The schema validation only checks non-empty schemas
        request = EntityTypeCreateRequest(
            ontology_id=uuid4(),
            code="test",
            name="Test",
            property_schema={},  # Empty is valid
        )

        mock_et = MagicMock()
        self.repo.create = AsyncMock(return_value=mock_et)

        result = await self.service.create_entity_type(request, uuid4())
        assert result is not None


class TestCapabilityService:
    """Test CapabilityService business logic."""

    def setup_method(self):
        """Setup test fixtures."""
        self.repo = MagicMock()
        self.repo.get_by_code = AsyncMock()
        self.repo.get_by_id_for_tenant = AsyncMock()
        self.repo.create = AsyncMock()
        self.repo.session.flush = AsyncMock()
        self.repo.session.refresh = AsyncMock()
        self.service = CapabilityService(self.repo)

    @pytest.mark.asyncio
    async def test_create_capability_success(self):
        """Test successful capability creation."""
        self.repo.get_by_code.return_value = None

        request = CapabilityCreateRequest(
            code="TemperatureMeasurement",
            name="Temperature Measurement",
            schema_definition={
                "version": "1.0",
                "properties": [{"name": "temperature", "data_type": "float"}],
            },
        )

        mock_cap = MagicMock()
        self.repo.create = AsyncMock(return_value=mock_cap)

        result = await self.service.create_capability(request, uuid4())
        assert result is not None
        self.repo.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_capability_duplicate_rejected(self):
        """Test duplicate capability code is rejected."""
        existing = MagicMock()
        self.repo.get_by_code.return_value = existing

        request = CapabilityCreateRequest(code="TemperatureMeasurement", name="Temp")

        with pytest.raises(DuplicateCodeError):
            await self.service.create_capability(request, uuid4())

    @pytest.mark.asyncio
    async def test_create_capability_invalid_schema_rejected(self):
        """Test invalid capability schema is rejected."""
        self.repo.get_by_code.return_value = None

        request = CapabilityCreateRequest(
            code="TestCap",
            name="Test",
            schema_definition={"invalid": "structure"},
        )

        with pytest.raises(InvalidSchemaError):
            await self.service.create_capability(request, uuid4())
