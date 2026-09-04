"""Test TwinDefinition persistence layer."""
import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4


class TestDefinitionRepository:
    """Tests for DefinitionRepository."""

    def setup_method(self):
        self.session = AsyncMock()
        from services.twin.repositories.definition_repository import DefinitionRepository
        self.repo = DefinitionRepository(self.session)

    @pytest.mark.asyncio
    async def test_get_by_code_found(self):
        from services.twin.models.definition import TwinDefinition
        definition = TwinDefinition(
            id=uuid4(), tenant_id=uuid4(), code="hvac_unit", name="HVAC Unit"
        )
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = definition
        self.session.execute.return_value = mock_result

        result = await self.repo.get_by_code("hvac_unit", definition.tenant_id)
        assert result is not None
        assert result.code == "hvac_unit"

    @pytest.mark.asyncio
    async def test_get_by_code_not_found(self):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        self.session.execute.return_value = mock_result

        result = await self.repo.get_by_code("nonexistent", uuid4())
        assert result is None

    @pytest.mark.asyncio
    async def test_list_by_tenant(self):
        from services.twin.models.definition import TwinDefinition
        definitions = [
            TwinDefinition(id=uuid4(), tenant_id=uuid4(), code=f"def{i}", name=f"Def {i}")
            for i in range(3)
        ]
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = definitions
        self.session.execute.return_value = mock_result

        result = await self.repo.list(tenant_id=definitions[0].tenant_id)
        assert len(result) == 3

    @pytest.mark.asyncio
    async def test_count_by_tenant(self):
        mock_result = MagicMock()
        mock_result.scalar_one.return_value = 5
        self.session.execute.return_value = mock_result

        count = await self.repo.count(tenant_id=uuid4())
        assert count == 5


class TestDefinitionService:
    """Tests for DefinitionService."""

    def setup_method(self):
        self.session = AsyncMock()
        from services.twin.services.definition_service import DefinitionService
        self.service = DefinitionService(self.session)

    @pytest.mark.asyncio
    async def test_create_definition_success(self):
        from services.twin.models.definition import TwinDefinition
        mock_repo = MagicMock()
        mock_repo.get_by_code = AsyncMock(return_value=None)
        mock_def = TwinDefinition(id=uuid4(), tenant_id=uuid4(), code="pump", name="Pump")
        mock_repo.create = AsyncMock(return_value=mock_def)
        self.service._repo = mock_repo

        result = await self.service.create(code="pump", name="Pump", tenant_id=mock_def.tenant_id)
        assert result.id == mock_def.id
        assert result.code == "pump"

    @pytest.mark.asyncio
    async def test_create_definition_duplicate_code_raises(self):
        from services.twin.models.definition import TwinDefinition
        from services.twin.exceptions import TwinDefinitionCodeExistsError
        existing = TwinDefinition(id=uuid4(), tenant_id=uuid4(), code="pump", name="Existing")
        mock_repo = MagicMock()
        mock_repo.get_by_code = AsyncMock(return_value=existing)
        self.service._repo = mock_repo

        with pytest.raises(TwinDefinitionCodeExistsError):
            await self.service.create(code="pump", name="Pump", tenant_id=existing.tenant_id)

    @pytest.mark.asyncio
    async def test_get_definition_found(self):
        from services.twin.models.definition import TwinDefinition
        definition = TwinDefinition(id=uuid4(), tenant_id=uuid4(), code="valve", name="Valve")
        mock_repo = MagicMock()
        mock_repo.get_by_id_for_tenant = AsyncMock(return_value=definition)
        self.service._repo = mock_repo

        result = await self.service.get(definition.id, definition.tenant_id)
        assert result.id == definition.id

    @pytest.mark.asyncio
    async def test_get_definition_not_found_raises(self):
        from services.twin.exceptions import TwinDefinitionNotFoundError
        mock_repo = MagicMock()
        mock_repo.get_by_id_for_tenant = AsyncMock(return_value=None)
        self.service._repo = mock_repo

        with pytest.raises(TwinDefinitionNotFoundError):
            await self.service.get(uuid4(), uuid4())

    @pytest.mark.asyncio
    async def test_update_definition(self):
        from services.twin.models.definition import TwinDefinition
        definition = TwinDefinition(id=uuid4(), tenant_id=uuid4(), code="sensor", name="Sensor")
        mock_repo = MagicMock()
        mock_repo.get_by_id_for_tenant = AsyncMock(return_value=definition)
        mock_repo.update = AsyncMock(return_value=definition)
        self.service._repo = mock_repo

        result = await self.service.update(definition.id, definition.tenant_id, name="Updated Sensor")
        assert result.name == "Updated Sensor"

    @pytest.mark.asyncio
    async def test_delete_definition(self):
        mock_repo = MagicMock()
        mock_repo.soft_delete = AsyncMock(return_value=True)
        self.service._repo = mock_repo

        result = await self.service.delete(uuid4(), uuid4())
        assert result is True

    @pytest.mark.asyncio
    async def test_list_definitions(self):
        from services.twin.models.definition import TwinDefinition
        definitions = [
            TwinDefinition(id=uuid4(), tenant_id=uuid4(), code=f"def{i}", name=f"Def {i}")
            for i in range(3)
        ]
        mock_repo = MagicMock()
        mock_repo.list = AsyncMock(return_value=definitions)
        self.service._repo = mock_repo

        result = await self.service.list(tenant_id=definitions[0].tenant_id)
        assert len(result) == 3

    @pytest.mark.asyncio
    async def test_count_definitions(self):
        mock_repo = MagicMock()
        mock_repo.count = AsyncMock(return_value=5)
        self.service._repo = mock_repo

        count = await self.service.count(uuid4())
        assert count == 5

    @pytest.mark.asyncio
    async def test_schema_validation_empty_accepted(self):
        """Test that empty schema is accepted during creation."""
        from services.twin.models.definition import TwinDefinition
        mock_repo = MagicMock()
        mock_repo.get_by_code = AsyncMock(return_value=None)
        mock_def = TwinDefinition(id=uuid4(), tenant_id=uuid4(), code="test", name="Test")
        mock_repo.create = AsyncMock(return_value=mock_def)
        self.service._repo = mock_repo

        result = await self.service.create(code="test", name="Test", tenant_id=uuid4(), schema={})
        assert result is not None

    @pytest.mark.asyncio
    async def test_tenant_isolation_in_create(self):
        """Test that code uniqueness is per-tenant."""
        from services.twin.models.definition import TwinDefinition
        from services.twin.exceptions import TwinDefinitionCodeExistsError
        tenant_a = uuid4()
        tenant_b = uuid4()

        mock_repo = MagicMock()

        async def side_effect(code, tid):
            return TwinDefinition(id=uuid4(), tenant_id=tid, code=code, name="Existing") if tid == tenant_a else None
        mock_repo.get_by_code = AsyncMock(side_effect=side_effect)
        created_def = TwinDefinition(id=uuid4(), tenant_id=tenant_b, code="test", name="Test B")
        mock_repo.create = AsyncMock(return_value=created_def)
        self.service._repo = mock_repo

        # Should succeed for tenant B
        result_b = await self.service.create(code="test", name="Test B", tenant_id=tenant_b)
        assert result_b is not None

        # Should fail for tenant A
        with pytest.raises(TwinDefinitionCodeExistsError):
            await self.service.create(code="test", name="Test A", tenant_id=tenant_a)
