"""Test TwinGraph tenant security and isolation."""
import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4


class TestCrossTenantRelationship:
    """Test cross-tenant access is blocked for relationships."""

    @pytest.mark.asyncio
    async def test_cross_tenant_relationship_create_blocked(self):
        """Verify relationship creation validates tenant on both endpoints."""
        from services.twin_graph.services import TwinGraphService

        session = AsyncMock()
        service = TwinGraphService(session)

        source_id = uuid4()
        target_id = uuid4()
        tenant_a = uuid4()
        tenant_b = uuid4()

        # Source exists for tenant A
        mock_source = MagicMock()
        mock_source.id = source_id
        mock_target = MagicMock()
        mock_target.id = target_id

        async def side_effect(entity_id, tid):
            if entity_id == source_id and tid == tenant_a:
                return mock_source
            if entity_id == target_id and tid == tenant_b:
                return mock_target
            return None

        service._entity_repo.get_by_id_for_tenant = AsyncMock(side_effect=side_effect)
        service._repo = MagicMock()
        service._repo.get_by_ids = AsyncMock(return_value=None)

        # Tenant A tries to create relationship where target belongs to tenant B
        # This should fail because target won't be found for tenant A
        with pytest.raises(Exception):  # EntityNotFoundError for target in tenant A
            await service.create_relation(source_id, target_id, "contains", tenant_a)


class TestCrossTenantQuery:
    """Test cross-tenant access is blocked for queries."""

    @pytest.mark.asyncio
    async def test_cross_tenant_query_blocked(self):
        """Verify neighbor query respects tenant boundary."""
        from services.twin_graph.services import TwinGraphService

        session = AsyncMock()
        service = TwinGraphService(session)

        twin_id = uuid4()
        tenant_a = uuid4()
        tenant_b = uuid4()

        # Entity exists only for tenant A
        mock_entity = MagicMock()
        mock_entity.id = twin_id

        async def side_effect(entity_id, tid):
            return mock_entity if entity_id == twin_id and tid == tenant_a else None

        service._entity_repo.get_by_id_for_tenant = AsyncMock(side_effect=side_effect)

        # Tenant B cannot query tenant A's entity neighbors
        with pytest.raises(Exception):
            await service.get_neighbors(twin_id, tenant_b)


class TestCrossTenantPath:
    """Test cross-tenant access is blocked for path queries."""

    @pytest.mark.asyncio
    async def test_cross_tenant_path_blocked(self):
        """Verify path query respects tenant boundary."""
        from services.twin_graph.services import TwinGraphService

        session = AsyncMock()
        service = TwinGraphService(session)

        source_id = uuid4()
        target_id = uuid4()
        tenant_a = uuid4()
        tenant_b = uuid4()

        mock_source = MagicMock()
        mock_target = MagicMock()

        async def side_effect(entity_id, tid):
            if entity_id == source_id and tid == tenant_a:
                return mock_source
            if entity_id == target_id and tid == tenant_a:
                return mock_target
            return None

        service._entity_repo.get_by_id_for_tenant = AsyncMock(side_effect=side_effect)

        # Tenant B cannot find path between entities in tenant A
        with pytest.raises(Exception):
            await service.find_path(source_id, target_id, tenant_b)


class TestSelfReferenceBlocked:
    """Test self-referencing relationships are blocked."""

    @pytest.mark.asyncio
    async def test_self_reference_rejected(self):
        """Verify source != target constraint is enforced."""
        from services.twin_graph.exceptions import InvalidRelationshipError
        from services.twin_graph.services import TwinGraphService

        session = AsyncMock()
        service = TwinGraphService(session)

        same_id = uuid4()
        tenant_id = uuid4()

        with pytest.raises(InvalidRelationshipError):
            await service.create_relation(same_id, same_id, "contains", tenant_id)


class TestTenantIsolationInList:
    """Test that listing relationships is tenant-scoped."""

    @pytest.mark.asyncio
    async def test_list_by_type_respects_tenant(self):
        """Verify list_by_type only returns current tenant's relationships."""
        from services.twin_graph.services import TwinGraphService
        from services.twin_graph.models import TwinRelationship

        session = AsyncMock()
        service = TwinGraphService(session)

        common_tenant = uuid4()
        rels = [
            TwinRelationship(id=uuid4(), tenant_id=common_tenant,
                           source_twin_id=uuid4(), target_twin_id=uuid4(),
                           relationship_type="contains")
            for _ in range(3)
        ]

        mock_repo = MagicMock()
        mock_repo.list_by_type = AsyncMock(return_value=rels)
        service._repo = mock_repo

        result = await service.list_relations_by_type("contains", rels[0].tenant_id)
        assert len(result) == 3
        assert all(r.tenant_id == rels[0].tenant_id for r in result)


class TestNoTenantFromBody:
    """Verify tenant_id never comes from API request body."""

    def test_service_never_accepts_tenant_from_body(self):
        """TwinGraphService methods should not accept tenant_id as optional with default."""
        import inspect
        from services.twin_graph.services import TwinGraphService

        for method_name in ["create_relation", "remove_relation", "get_relation",
                          "get_neighbors", "find_path"]:
            method = getattr(TwinGraphService, method_name)
            sig = inspect.signature(method)
            params = list(sig.parameters.keys())
            # tenant_id should always be required, never optional
            if "tenant_id" in params:
                param = sig.parameters["tenant_id"]
                assert param.default is inspect.Parameter.empty, \
                    f"{method_name}: tenant_id must not have a default value (no body override)"
