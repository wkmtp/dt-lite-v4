"""Test TwinRelationshipRepository."""
import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4


class TestTwinRelationshipRepository:
    """Tests for TwinRelationshipRepository."""

    def setup_method(self):
        self.session = AsyncMock()
        from services.twin_graph.repositories import TwinRelationshipRepository
        self.repo = TwinRelationshipRepository(self.session)

    @pytest.mark.asyncio
    async def test_get_by_ids_found(self):
        from services.twin_graph.models import TwinRelationship
        rel = TwinRelationship(
            id=uuid4(), tenant_id=uuid4(),
            source_twin_id=uuid4(), target_twin_id=uuid4(),
            relationship_type="contains",
        )
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = rel
        self.session.execute.return_value = mock_result

        result = await self.repo.get_by_ids(rel.source_twin_id, rel.target_twin_id, rel.tenant_id)
        assert result is not None
        assert result.relationship_type == "contains"

    @pytest.mark.asyncio
    async def test_get_by_ids_not_found(self):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        self.session.execute.return_value = mock_result

        result = await self.repo.get_by_ids(uuid4(), uuid4(), uuid4())
        assert result is None

    @pytest.mark.asyncio
    async def test_list_source_relationships(self):
        from services.twin_graph.models import TwinRelationship
        rels = [
            TwinRelationship(id=uuid4(), tenant_id=uuid4(),
                           source_twin_id=uuid4(), target_twin_id=uuid4(),
                           relationship_type="contains")
            for _ in range(3)
        ]
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = rels
        self.session.execute.return_value = mock_result

        result = await self.repo.list_source_relationships(uuid4(), uuid4())
        assert len(result) == 3

    @pytest.mark.asyncio
    async def test_list_target_relationships(self):
        from services.twin_graph.models import TwinRelationship
        rels = [
            TwinRelationship(id=uuid4(), tenant_id=uuid4(),
                           source_twin_id=uuid4(), target_twin_id=uuid4(),
                           relationship_type="located_in")
            for _ in range(2)
        ]
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = rels
        self.session.execute.return_value = mock_result

        result = await self.repo.list_target_relationships(uuid4(), uuid4())
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_list_by_type(self):
        from services.twin_graph.models import TwinRelationship
        rels = [
            TwinRelationship(id=uuid4(), tenant_id=uuid4(),
                           source_twin_id=uuid4(), target_twin_id=uuid4(),
                           relationship_type="controls")
            for _ in range(4)
        ]
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = rels
        self.session.execute.return_value = mock_result

        result = await self.repo.list_by_type("controls", uuid4())
        assert len(result) == 4
        assert all(r.relationship_type == "controls" for r in result)

    @pytest.mark.asyncio
    async def test_count_by_type(self):
        mock_result = MagicMock()
        mock_result.scalar_one.return_value = 7
        self.session.execute.return_value = mock_result

        count = await self.repo.count_by_type("monitored_by", uuid4())
        assert count == 7

    @pytest.mark.asyncio
    async def test_tenant_filtering_in_list_source(self):
        from services.twin_graph.models import TwinRelationship
        tenant_id = uuid4()
        rels = [
            TwinRelationship(id=uuid4(), tenant_id=tenant_id,
                           source_twin_id=uuid4(), target_twin_id=uuid4(),
                           relationship_type="contains")
        ]
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = rels
        self.session.execute.return_value = mock_result

        result = await self.repo.list_source_relationships(uuid4(), tenant_id)
        assert len(result) == 1
        assert all(r.tenant_id == tenant_id for r in result)

    @pytest.mark.asyncio
    async def test_get_by_id_for_tenant(self):
        from services.twin_graph.models import TwinRelationship
        rel = TwinRelationship(id=uuid4(), tenant_id=uuid4(),
                              source_twin_id=uuid4(), target_twin_id=uuid4(),
                              relationship_type="depends_on")
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = rel
        self.session.execute.return_value = mock_result

        result = await self.repo.get_by_id_for_tenant(rel.id, rel.tenant_id)
        assert result is not None
        assert result.id == rel.id
