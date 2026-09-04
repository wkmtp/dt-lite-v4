"""Test TwinQueryEngine graph traversal."""
import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4


class TestTwinQueryEngine:
    """Tests for TwinQueryEngine neighbor and path queries."""

    def setup_method(self):
        self.repo = MagicMock()
        self.repo.list_source_relationships = AsyncMock()
        self.repo.list_target_relationships = AsyncMock()
        from services.twin_graph.query import TwinQueryEngine
        self.engine = TwinQueryEngine(self.repo)

    @pytest.mark.asyncio
    async def test_get_neighbors_outgoing(self):
        """Test getting outgoing neighbors."""
        from services.twin_graph.models import TwinRelationship
        source_id = uuid4()
        target_id1 = uuid4()
        target_id2 = uuid4()
        rel1 = TwinRelationship(
            source_twin_id=source_id, target_twin_id=target_id1,
            relationship_type="contains",
        )
        rel2 = TwinRelationship(
            source_twin_id=source_id, target_twin_id=target_id2,
            relationship_type="controls",
        )
        self.repo.list_source_relationships = AsyncMock(return_value=[rel1, rel2])
        self.repo.list_target_relationships = AsyncMock(return_value=[])

        neighbors = await self.engine.get_neighbors(source_id, uuid4(), direction="outgoing")
        assert len(neighbors) == 2
        assert all(n["direction"] == "outgoing" for n in neighbors)

    @pytest.mark.asyncio
    async def test_get_neighbors_incoming(self):
        """Test getting incoming neighbors."""
        from services.twin_graph.models import TwinRelationship
        source_id = uuid4()
        target_id = uuid4()
        rel1 = TwinRelationship(
            source_twin_id=source_id, target_twin_id=target_id,
            relationship_type="located_in",
        )
        self.repo.list_source_relationships = AsyncMock(return_value=[])
        self.repo.list_target_relationships = AsyncMock(return_value=[rel1])

        neighbors = await self.engine.get_neighbors(target_id, uuid4(), direction="incoming")
        assert len(neighbors) == 1
        assert neighbors[0]["direction"] == "incoming"

    @pytest.mark.asyncio
    async def test_get_neighbors_both_directions(self):
        """Test getting neighbors in both directions."""
        from services.twin_graph.models import TwinRelationship
        center_id = uuid4()
        out_rel = TwinRelationship(source_twin_id=center_id, target_twin_id=uuid4(),
                                   relationship_type="contains")
        in_rel = TwinRelationship(source_twin_id=uuid4(), target_twin_id=center_id,
                                  relationship_type="hosts")
        self.repo.list_source_relationships = AsyncMock(return_value=[out_rel])
        self.repo.list_target_relationships = AsyncMock(return_value=[in_rel])

        neighbors = await self.engine.get_neighbors(center_id, uuid4())
        assert len(neighbors) == 2

    @pytest.mark.asyncio
    async def test_find_path_found(self):
        """Test finding a path between two entities."""
        from services.twin_graph.models import TwinRelationship
        id_a = uuid4()
        id_b = uuid4()
        id_c = uuid4()

        rel_ab = TwinRelationship(source_twin_id=id_a, target_twin_id=id_b, relationship_type="contains")
        rel_bc = TwinRelationship(source_twin_id=id_b, target_twin_id=id_c, relationship_type="contains")

        # BFS: A -> B -> C
        async def mock_source(sid, tid):
            if sid == id_a:
                return [rel_ab]
            elif sid == id_b:
                return [rel_bc]
            return []

        self.repo.list_source_relationships = AsyncMock(side_effect=mock_source)
        self.repo.list_target_relationships = AsyncMock(return_value=[])

        path = await self.engine.find_path(id_a, id_c, uuid4(), max_depth=3)
        assert path is not None
        assert len(path) == 3  # A, B, C

    @pytest.mark.asyncio
    async def test_find_path_no_path(self):
        """Test when no path exists."""
        self.repo.list_source_relationships = AsyncMock(return_value=[])
        self.repo.list_target_relationships = AsyncMock(return_value=[])

        path = await self.engine.find_path(uuid4(), uuid4(), uuid4())
        assert path is None

    @pytest.mark.asyncio
    async def test_find_path_same_entity(self):
        """Test path from entity to itself."""
        same_id = uuid4()
        path = await self.engine.find_path(same_id, same_id, uuid4())
        assert path is not None
        assert len(path) == 1

    @pytest.mark.asyncio
    async def test_find_path_respects_max_depth(self):
        """Test that path query respects max_depth limit."""
        from services.twin_graph.models import TwinRelationship
        id_a = uuid4()
        id_b = uuid4()
        id_c = uuid4()

        rel_ab = TwinRelationship(source_twin_id=id_a, target_twin_id=id_b, relationship_type="contains")

        async def mock_source(sid, tid):
            if sid == id_a:
                return [rel_ab]
            return []

        self.repo.list_source_relationships = AsyncMock(side_effect=mock_source)
        self.repo.list_target_relationships = AsyncMock(return_value=[])

        # max_depth=1 should only find direct neighbors, not path to C
        path = await self.engine.find_path(id_a, id_c, uuid4(), max_depth=1)
        assert path is None

    @pytest.mark.asyncio
    async def test_get_neighbors_empty(self):
        """Test getting neighbors when none exist."""
        self.repo.list_source_relationships = AsyncMock(return_value=[])
        self.repo.list_target_relationships = AsyncMock(return_value=[])

        neighbors = await self.engine.get_neighbors(uuid4(), uuid4())
        assert neighbors == []
