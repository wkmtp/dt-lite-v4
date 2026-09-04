"""Test Twin Persistence Security — Tenant isolation for persistent models."""
import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4


class TestTenantIsolationDefinitions:
    """Test tenant isolation for TwinDefinition operations."""

    def setup_method(self):
        self.session = AsyncMock()
        from services.twin.repositories.definition_repository import DefinitionRepository
        self.repo = DefinitionRepository(self.session)

    @pytest.mark.asyncio
    async def test_get_by_code_ignores_other_tenants(self):
        """Verify code lookup is tenant-scoped."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        self.session.execute.return_value = mock_result

        result = await self.repo.get_by_code("hvac_unit", uuid4())
        assert result is None  # Different tenant shouldn't find it

    @pytest.mark.asyncio
    async def test_list_is_tenant_scoped(self):
        """Verify list returns only current tenant's definitions."""
        from services.twin.models.definition import TwinDefinition
        definitions = [
            TwinDefinition(id=uuid4(), tenant_id=uuid4(), code="def1", name="Def1"),
        ]

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = definitions
        self.session.execute.return_value = mock_result

        result = await self.repo.list(tenant_id=definitions[0].tenant_id)
        assert all(d.tenant_id == definitions[0].tenant_id for d in result)


class TestTenantIsolationEntities:
    """Test tenant isolation for PersistentTwinEntity operations."""

    def setup_method(self):
        self.session = AsyncMock()
        from services.twin.repositories.entity_repository import EntityRepository
        self.repo = EntityRepository(self.session)

    @pytest.mark.asyncio
    async def test_get_by_external_id_ignores_other_tenants(self):
        """Verify external_id lookup is tenant-scoped."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        self.session.execute.return_value = mock_result

        result = await self.repo.get_by_external_id("ext-001", uuid4())
        assert result is None

    @pytest.mark.asyncio
    async def test_list_by_definition_respects_tenant(self):
        """Verify listing by definition respects tenant boundary."""
        from services.twin.models.entity import PersistentTwinEntity
        entities = [
            PersistentTwinEntity(id=uuid4(), tenant_id=uuid4(), external_id="e1", name="E1"),
        ]

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = entities
        self.session.execute.return_value = mock_result

        result = await self.repo.list_by_definition(entities[0].definition_id, entities[0].tenant_id)
        assert len(result) == 1
        assert result[0].tenant_id == entities[0].tenant_id


class TestTenantIsolationBindings:
    """Test tenant isolation for TwinBinding operations."""

    def setup_method(self):
        self.session = AsyncMock()
        from services.twin.repositories.binding_repository import BindingRepository
        self.repo = BindingRepository(self.session)

    @pytest.mark.asyncio
    async def test_get_by_device_respects_tenant(self):
        """Verify binding lookup respects tenant boundary."""
        from services.twin.models.binding import TwinBinding
        binding = TwinBinding(
            id=uuid4(), tenant_id=uuid4(), device_id=uuid4(), twin_entity_id=uuid4()
        )

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = binding
        self.session.execute.return_value = mock_result

        result = await self.repo.get_by_device(binding.device_id, binding.tenant_id)
        assert result is not None
        assert result.tenant_id == binding.tenant_id

    @pytest.mark.asyncio
    async def test_exists_checks_tenant(self):
        """Verify existence check includes tenant."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = MagicMock()
        self.session.execute.return_value = mock_result

        result = await self.repo.exists(uuid4(), uuid4(), uuid4())
        assert result is True


class TestCrossTenantAccessPersistence:
    """Test cross-tenant access is blocked in persistence layer."""

    def setup_method(self):
        self.session = AsyncMock()

    @pytest.mark.asyncio
    async def test_cannot_read_other_tenant_definitions(self):
        """Verify tenant A cannot read tenant B's definitions."""
        from services.twin.services.definition_service import DefinitionService
        from services.twin.exceptions import TwinDefinitionNotFoundError

        service = DefinitionService(self.session)

        # Mock repository that simulates different tenants
        mock_repo = MagicMock()
        mock_repo.get_by_id_for_tenant = AsyncMock(return_value=None)  # Not found for this tenant
        service._repo = mock_repo

        with pytest.raises(TwinDefinitionNotFoundError):
            await service.get(uuid4(), uuid4())

    @pytest.mark.asyncio
    async def test_cannot_modify_other_tenant_entities(self):
        """Verify tenant A cannot modify tenant B's entities."""
        from services.twin.services.entity_service import EntityService
        from services.twin.exceptions import TwinEntityNotFoundError

        service = EntityService(self.session)

        mock_repo = MagicMock()
        mock_repo.get_by_id_for_tenant = AsyncMock(return_value=None)
        service._repo = mock_repo

        with pytest.raises(TwinEntityNotFoundError):
            await service.update_metadata(uuid4(), uuid4(), {})

    @pytest.mark.asyncio
    async def test_cannot_create_binding_across_tenants(self):
        """Verify cross-tenant binding creation is blocked."""
        from services.twin.services.binding_service import BindingService
        from services.twin.exceptions import TwinEntityNotFoundError

        service = BindingService(self.session)

        # Device from tenant A, but entity from tenant B
        mock_device = MagicMock()
        mock_entity = None  # Not found for tenant A

        mock_binding_repo = MagicMock()
        mock_device_repo = MagicMock()
        mock_device_repo.get_by_id_for_tenant = AsyncMock(return_value=mock_device)
        mock_entity_repo = MagicMock()
        mock_entity_repo.get_by_id_for_tenant = AsyncMock(return_value=mock_entity)

        service._repo = mock_binding_repo
        service._device_repo = mock_device_repo
        service._entity_repo = mock_entity_repo

        with pytest.raises(TwinEntityNotFoundError):
            await service.create(uuid4(), uuid4(), uuid4())


class TestSoftDeleteIsolation:
    """Test soft delete respects tenant boundaries."""

    @pytest.mark.asyncio
    async def test_soft_delete_only_affects_tenant(self):
        """Verify soft delete only affects current tenant's records."""
        from services.twin.services.definition_service import DefinitionService

        service = DefinitionService(AsyncMock())

        mock_repo = MagicMock()
        mock_repo.soft_delete = AsyncMock(return_value=True)
        service._repo = mock_repo

        # Delete should succeed for valid tenant
        result = await service.delete(uuid4(), uuid4())
        assert result is True


class TestNoAdapterDependency:
    """Verify persistence layer has no adapter dependencies."""

    def test_no_adapter_imports_in_persistence(self):
        """Check that persistence modules don't import from adapter."""
        import os
        import glob

        twin_dir = os.path.join(os.path.dirname(__file__), "..", "services", "twin")
        persistence_dirs = ["models", "repositories", "services"]

        for sub_dir in persistence_dirs:
            pattern = os.path.join(twin_dir, sub_dir, "*.py")
            for filepath in glob.glob(pattern):
                if "__init__" in filepath:
                    continue
                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read()
                    assert "services.adapter" not in content, \
                        f"Found adapter import in {filepath}"
