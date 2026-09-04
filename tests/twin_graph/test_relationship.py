"""Test TwinGraphService relationship operations."""
import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4


class TestTwinGraphService:
    """Tests for TwinGraphService."""

    def setup_method(self):
        self.session = AsyncMock()
        from services.twin_graph.services import TwinGraphService
        self.service = TwinGraphService(self.session)

    @pytest.mark.asyncio
    async def test_create_relation_success(self):
        """Test successful relationship creation."""
        from services.twin_graph.models import TwinRelationship

        source_id = uuid4()
        target_id = uuid4()
        tenant_id = uuid4()

        # Mock entity repo
        mock_entity = MagicMock()
        mock_entity.id = source_id
        self.service._entity_repo.get_by_id_for_tenant = AsyncMock(return_value=mock_entity)

        # Mock relationship repo
        mock_rel_repo = MagicMock()
        mock_rel_repo.get_by_ids = AsyncMock(return_value=None)
        mock_rel = TwinRelationship(
            id=uuid4(), tenant_id=tenant_id,
            source_twin_id=source_id, target_twin_id=target_id,
            relationship_type="contains",
        )
        mock_rel_repo.create = AsyncMock(return_value=mock_rel)
        self.service._repo = mock_rel_repo

        result = await self.service.create_relation(source_id, target_id, "contains", tenant_id)
        assert result.source_twin_id == source_id
        assert result.target_twin_id == target_id
        assert result.relationship_type == "contains"

    @pytest.mark.asyncio
    async def test_create_relation_self_reference_rejected(self):
        """Test that self-referencing relationships are rejected."""
        from services.twin_graph.exceptions import InvalidRelationshipError

        same_id = uuid4()
        with pytest.raises(InvalidRelationshipError):
            await self.service.create_relation(same_id, same_id, "contains", uuid4())

    @pytest.mark.asyncio
    async def test_create_relation_source_not_found(self):
        """Test that missing source entity raises error."""
        from services.twin_graph.exceptions import TwinEntityNotFoundError

        self.service._entity_repo.get_by_id_for_tenant = AsyncMock(return_value=None)

        with pytest.raises(TwinEntityNotFoundError):
            await self.service.create_relation(uuid4(), uuid4(), "contains", uuid4())

    @pytest.mark.asyncio
    async def test_create_relation_duplicate_rejected(self):
        """Test that duplicate relationships are rejected."""
        from services.twin_graph.exceptions import InvalidRelationshipError
        from services.twin_graph.models import TwinRelationship

        existing = TwinRelationship(
            id=uuid4(), tenant_id=uuid4(),
            source_twin_id=uuid4(), target_twin_id=uuid4(),
            relationship_type="contains",
        )

        mock_entity = MagicMock()
        self.service._entity_repo.get_by_id_for_tenant = AsyncMock(return_value=mock_entity)

        mock_rel_repo = MagicMock()
        mock_rel_repo.get_by_ids = AsyncMock(return_value=existing)
        self.service._repo = mock_rel_repo

        with pytest.raises(InvalidRelationshipError):
            await self.service.create_relation(
                existing.source_twin_id, existing.target_twin_id,
                "contains", existing.tenant_id,
            )

    @pytest.mark.asyncio
    async def test_remove_relation_success(self):
        """Test successful relationship removal."""
        from services.twin_graph.models import TwinRelationship

        rel = TwinRelationship(id=uuid4(), tenant_id=uuid4(),
                              source_twin_id=uuid4(), target_twin_id=uuid4(),
                              relationship_type="contains")

        mock_rel_repo = MagicMock()
        mock_rel_repo.get_by_id_for_tenant = AsyncMock(return_value=rel)
        mock_rel_repo.soft_delete = AsyncMock(return_value=True)
        self.service._repo = mock_rel_repo

        result = await self.service.remove_relation(rel.id, rel.tenant_id)
        assert result is True

    @pytest.mark.asyncio
    async def test_remove_relation_not_found(self):
        """Test removal of non-existent relationship raises error."""
        from services.twin_graph.exceptions import TwinRelationshipNotFoundError

        mock_rel_repo = MagicMock()
        mock_rel_repo.get_by_id_for_tenant = AsyncMock(return_value=None)
        self.service._repo = mock_rel_repo

        with pytest.raises(TwinRelationshipNotFoundError):
            await self.service.remove_relation(uuid4(), uuid4())

    @pytest.mark.asyncio
    async def test_get_relation_success(self):
        """Test retrieving an existing relationship."""
        from services.twin_graph.models import TwinRelationship

        rel = TwinRelationship(id=uuid4(), tenant_id=uuid4(),
                              source_twin_id=uuid4(), target_twin_id=uuid4(),
                              relationship_type="controls")

        mock_rel_repo = MagicMock()
        mock_rel_repo.get_by_id_for_tenant = AsyncMock(return_value=rel)
        self.service._repo = mock_rel_repo

        result = await self.service.get_relation(rel.id, rel.tenant_id)
        assert result.id == rel.id

    @pytest.mark.asyncio
    async def test_get_relation_not_found(self):
        """Test that getting a non-existent relationship raises error."""
        from services.twin_graph.exceptions import TwinRelationshipNotFoundError

        mock_rel_repo = MagicMock()
        mock_rel_repo.get_by_id_for_tenant = AsyncMock(return_value=None)
        self.service._repo = mock_rel_repo

        with pytest.raises(TwinRelationshipNotFoundError):
            await self.service.get_relation(uuid4(), uuid4())
