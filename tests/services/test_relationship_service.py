"""RelationshipService Tests for Phase 1 Task 3"""
import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock, AsyncMock
from uuid import uuid4

from services.core.models.models import Entity
from services.core.services.relationship_service import RelationshipService
from services.core.schemas.relationship import RelationshipCreate
from services.core.unit_of_work import UnitOfWork
from services.exceptions.base import EntityNotFound


class TestRelationshipService:
    """Test RelationshipService operations."""

    def _make_mock_rel(self, **kwargs):
        """Create a mock relationship."""
        now = datetime.now(timezone.utc)
        rel = MagicMock()
        rel.id = kwargs.get("id", uuid4())
        rel.tenant_id = kwargs.get("tenant_id", uuid4())
        rel.source_entity_id = kwargs.get("source_entity_id", uuid4())
        rel.target_entity_id = kwargs.get("target_entity_id", uuid4())
        rel.relation_type = kwargs.get("relation_type", "contains")
        rel.extra_data = kwargs.get("extra_data", {})
        rel.created_at = kwargs.get("created_at", now)
        rel.deleted_at = None
        return rel

    @pytest.mark.asyncio
    async def test_create_relationship_success(self):
        """Test creating a valid relationship."""
        uow = MagicMock(spec=UnitOfWork)
        uow.entities = MagicMock()
        uow.relationships = MagicMock()
        uow.commit = AsyncMock()

        # Mock entities exist
        source_entity = Entity(id=uuid4(), tenant_id=uuid4(), entity_type="building", name="Building")
        target_entity = Entity(id=uuid4(), tenant_id=source_entity.tenant_id, entity_type="room", name="Room")
        uow.entities.get_by_id = AsyncMock(side_effect=[source_entity, target_entity])

        # Mock relationship creation
        mock_rel = self._make_mock_rel(
            tenant_id=source_entity.tenant_id,
            source_entity_id=source_entity.id,
            target_entity_id=target_entity.id,
            relation_type="contains"
        )
        uow.relationships.create_relation = AsyncMock(return_value=mock_rel)

        service = RelationshipService(uow)

        data = RelationshipCreate(
            source_entity_id=source_entity.id,
            target_entity_id=target_entity.id,
            relation_type="contains",
        )

        result, event = await service.create_relationship(data, source_entity.tenant_id)

        assert result is not None
        assert result.relation_type == "contains"
        uow.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_relationship_self_loop(self):
        """Test that self-loop relationships are rejected."""
        uow = MagicMock(spec=UnitOfWork)
        service = RelationshipService(uow)

        entity_id = uuid4()
        data = RelationshipCreate(
            source_entity_id=entity_id,
            target_entity_id=entity_id,  # Same entity!
            relation_type="contains",
        )

        with pytest.raises(ValueError):
            await service.create_relationship(data, uuid4())

    @pytest.mark.asyncio
    async def test_create_relationship_source_not_found(self):
        """Test creating relationship with non-existent source entity."""
        uow = MagicMock(spec=UnitOfWork)
        uow.entities = MagicMock()
        uow.commit = AsyncMock()

        uow.entities.get_by_id = AsyncMock(return_value=None)

        service = RelationshipService(uow)

        data = RelationshipCreate(
            source_entity_id=uuid4(),
            target_entity_id=uuid4(),
            relation_type="contains",
        )

        with pytest.raises(EntityNotFound):
            await service.create_relationship(data, uuid4())

    @pytest.mark.asyncio
    async def test_delete_relationship(self):
        """Test soft deleting a relationship."""
        uow = MagicMock(spec=UnitOfWork)
        uow.relationships = MagicMock()
        uow.commit = AsyncMock()

        uow.relationships.delete_relation = AsyncMock(return_value=True)

        service = RelationshipService(uow)
        result = await service.delete_relationship(uuid4(), uuid4())

        assert result is True

    @pytest.mark.asyncio
    async def test_get_children(self):
        """Test getting child entities."""
        uow = MagicMock(spec=UnitOfWork)
        uow.relationships = MagicMock()

        mock_rels = [
            self._make_mock_rel(relation_type="contains")
        ]
        uow.relationships.list_source_relations = AsyncMock(return_value=mock_rels)

        service = RelationshipService(uow)
        children = await service.get_children(uuid4(), uuid4())

        assert len(children) == 1

    @pytest.mark.asyncio
    async def test_get_parents(self):
        """Test getting parent entities."""
        uow = MagicMock(spec=UnitOfWork)
        uow.relationships = MagicMock()

        mock_rels = [
            self._make_mock_rel(relation_type="part_of")
        ]
        uow.relationships.list_target_relations = AsyncMock(return_value=mock_rels)

        service = RelationshipService(uow)
        parents = await service.get_parents(uuid4(), uuid4())

        assert len(parents) == 1
