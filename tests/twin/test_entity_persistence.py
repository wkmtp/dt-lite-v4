"""Test PersistentTwinEntity persistence layer."""
import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4


class TestEntityRepository:
    """Tests for EntityRepository."""

    def setup_method(self):
        self.session = AsyncMock()
        from services.twin.repositories.entity_repository import EntityRepository
        self.repo = EntityRepository(self.session)

    @pytest.mark.asyncio
    async def test_get_by_external_id_found(self):
        from services.twin.models.entity import PersistentTwinEntity
        entity = PersistentTwinEntity(
            id=uuid4(), tenant_id=uuid4(), definition_id=uuid4(),
            external_id="device-001", name="Device 001"
        )
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = entity
        self.session.execute.return_value = mock_result

        result = await self.repo.get_by_external_id("device-001", entity.tenant_id)
        assert result is not None
        assert result.external_id == "device-001"

    @pytest.mark.asyncio
    async def test_get_by_external_id_not_found(self):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        self.session.execute.return_value = mock_result

        result = await self.repo.get_by_external_id("nonexistent", uuid4())
        assert result is None

    @pytest.mark.asyncio
    async def test_list_by_definition(self):
        from services.twin.models.entity import PersistentTwinEntity
        entities = [
            PersistentTwinEntity(
                id=uuid4(), tenant_id=uuid4(), definition_id=uuid4(),
                external_id=f"dev{i}", name=f"Device {i}"
            )
            for i in range(3)
        ]
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = entities
        self.session.execute.return_value = mock_result

        result = await self.repo.list_by_definition(entities[0].definition_id, entities[0].tenant_id)
        assert len(result) == 3

    @pytest.mark.asyncio
    async def test_count_by_definition(self):
        mock_result = MagicMock()
        mock_result.scalar_one.return_value = 10
        self.session.execute.return_value = mock_result

        count = await self.repo.count_by_definition(uuid4(), uuid4())
        assert count == 10


class TestEntityService:
    """Tests for EntityService."""

    def setup_method(self):
        self.session = AsyncMock()
        from services.twin.services.entity_service import EntityService
        self.service = EntityService(self.session)

    @pytest.mark.asyncio
    async def test_create_entity_success(self):
        from services.twin.models.entity import PersistentTwinEntity
        mock_ent_repo = MagicMock()
        mock_ent = PersistentTwinEntity(
            id=uuid4(), tenant_id=uuid4(),
            definition_id=uuid4(), external_id="dev-001", name="Device 001"
        )
        mock_ent_repo.create = AsyncMock(return_value=mock_ent)
        self.service._repo = mock_ent_repo

        result = await self.service.create(
            external_id="dev-001", name="Device 001",
            definition_id=mock_ent.definition_id, tenant_id=mock_ent.tenant_id
        )
        assert result.id == mock_ent.id

    @pytest.mark.asyncio
    async def test_get_entity_found(self):
        from services.twin.models.entity import PersistentTwinEntity
        entity = PersistentTwinEntity(
            id=uuid4(), tenant_id=uuid4(), definition_id=uuid4(),
            external_id="dev-001", name="Device 001"
        )
        mock_repo = MagicMock()
        mock_repo.get_by_id_for_tenant = AsyncMock(return_value=entity)
        self.service._repo = mock_repo

        result = await self.service.get(entity.id, entity.tenant_id)
        assert result.id == entity.id

    @pytest.mark.asyncio
    async def test_get_entity_not_found_raises(self):
        from services.twin.exceptions import TwinEntityNotFoundError
        mock_repo = MagicMock()
        mock_repo.get_by_id_for_tenant = AsyncMock(return_value=None)
        self.service._repo = mock_repo

        with pytest.raises(TwinEntityNotFoundError):
            await self.service.get(uuid4(), uuid4())

    @pytest.mark.asyncio
    async def test_update_metadata(self):
        from services.twin.models.entity import PersistentTwinEntity
        entity = PersistentTwinEntity(
            id=uuid4(), tenant_id=uuid4(), definition_id=uuid4(),
            external_id="dev-001", name="Device 001"
        )
        mock_repo = MagicMock()
        mock_repo.get_by_id_for_tenant = AsyncMock(return_value=entity)
        mock_repo.update = AsyncMock(return_value=entity)
        self.service._repo = mock_repo

        result = await self.service.update_metadata(
            entity.id, entity.tenant_id, {"custom": "data"}
        )
        assert result.meta_data == {"custom": "data"}

    @pytest.mark.asyncio
    async def test_delete_entity(self):
        mock_repo = MagicMock()
        mock_repo.soft_delete = AsyncMock(return_value=True)
        self.service._repo = mock_repo

        result = await self.service.delete(uuid4(), uuid4())
        assert result is True

    @pytest.mark.asyncio
    async def test_list_entities(self):
        from services.twin.models.entity import PersistentTwinEntity
        entities = [
            PersistentTwinEntity(
                id=uuid4(), tenant_id=uuid4(), definition_id=uuid4(),
                external_id=f"dev{i}", name=f"Device {i}"
            )
            for i in range(3)
        ]
        mock_repo = MagicMock()
        mock_repo.list = AsyncMock(return_value=entities)
        self.service._repo = mock_repo

        result = await self.service.list(tenant_id=entities[0].tenant_id)
        assert len(result) == 3

    @pytest.mark.asyncio
    async def test_count_entities(self):
        mock_repo = MagicMock()
        mock_repo.count = AsyncMock(return_value=10)
        self.service._repo = mock_repo

        count = await self.service.count(uuid4())
        assert count == 10

    @pytest.mark.asyncio
    async def test_create_with_metadata(self):
        from services.twin.models.entity import PersistentTwinEntity
        mock_ent_repo = MagicMock()
        mock_ent = PersistentTwinEntity(
            id=uuid4(), tenant_id=uuid4(),
            definition_id=uuid4(), external_id="dev-002", name="Device 002"
        )
        mock_ent.meta_data = {"custom": "value"}
        mock_ent_repo.create = AsyncMock(return_value=mock_ent)
        self.service._repo = mock_ent_repo

        result = await self.service.create(
            external_id="dev-002", name="Device 002",
            definition_id=uuid4(), tenant_id=uuid4(),
            metadata={"custom": "value"}
        )
        assert result.meta_data == {"custom": "value"}

    @pytest.mark.asyncio
    async def test_tenant_isolation_in_get(self):
        """Verify get uses tenant-scoped repository method."""
        from services.twin.models.entity import PersistentTwinEntity
        from services.twin.exceptions import TwinEntityNotFoundError
        entity = PersistentTwinEntity(
            id=uuid4(), tenant_id=uuid4(), definition_id=uuid4(),
            external_id="dev-001", name="Device 001"
        )
        mock_repo = MagicMock()
        mock_repo.get_by_id_for_tenant = AsyncMock(return_value=entity)
        self.service._repo = mock_repo

        # Should find entity with correct tenant
        result = await self.service.get(entity.id, entity.tenant_id)
        assert result.id == entity.id

        # Should not find with wrong tenant
        mock_repo.get_by_id_for_tenant = AsyncMock(return_value=None)
        with pytest.raises(TwinEntityNotFoundError):
            await self.service.get(entity.id, uuid4())
