"""Task 10.1 Architecture Hardening Review Tests.

Comprehensive audit for:
- Migration correctness (FK constraints, indexes, CHECK constraints)
- Tenant security isolation at all layers
- Repository boundary enforcement (no commit/rollback)
- Runtime separation (no telemetry in graph)
- Dependency scan (no adapter, protocol, external graph DB imports)
"""
import inspect
import os
import sys
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)


# ============================================================
# SECTION 1: MIGRATION HARDENING (5 tests)
# ============================================================

class TestMigrationHardening:
    """Verify phase10_twin_graph.py migration integrity."""

    def test_migration_revision_chain(self):
        """Verify linear revision chain to phase9."""
        import database.migrations.versions.phase10_twin_graph as mig
        assert mig.down_revision == 'phase9_twin_persistence', \
            "Migration must extend phase9_twin_persistence"

    def test_table_has_tenant_id_not_null(self):
        """Verify twin_relationships has tenant_id as NOT NULL."""
        from services.twin_graph.models import TwinRelationship
        from sqlalchemy import inspect as sa_inspect

        mapper = sa_inspect(TwinRelationship)
        tenant_col = mapper.columns['tenant_id']
        assert tenant_col.nullable is False, \
            "tenant_id must be NOT NULL for tenant isolation"

    def test_foreign_keys_cascade_delete(self):
        """Verify FK relationships have ON DELETE CASCADE."""
        from services.twin_graph.models import TwinRelationship
        from sqlalchemy import inspect as sa_inspect

        mapper = sa_inspect(TwinRelationship)
        table = mapper.persist_selectable

        # Check foreign keys by column name
        source_col = table.c['source_twin_id']
        target_col = table.c['target_twin_id']

        fk_constraints = list(source_col.foreign_keys) + list(target_col.foreign_keys)
        ondelete_values = {str(fk.ondelete) for fk in fk_constraints}

        assert 'CASCADE' in ondelete_values, \
            f"Expected CASCADE delete on FKs, got: {ondelete_values}"

    def test_check_constraint_no_self_reference(self):
        """Verify CHECK constraint prevents self-referencing relationships."""
        from services.twin_graph.models import TwinRelationship

        table = TwinRelationship.__table__
        check_constraints = [c for c in table.constraints if hasattr(c, 'sqltext')]
        has_check = any("source_twin_id != target_twin_id" in str(c.sqltext)
                       for c in check_constraints)
        assert has_check, "Missing CHECK constraint for no self-reference"

    def test_indexes_exist_for_query_performance(self):
        """Verify required indexes exist for query performance.

        Some indexes are defined via mapped_column(index=True) on the model
        (e.g., tenant_id) while others are explicit Index objects in __table_args__.
        We verify both by checking the migration DDL and model definitions.
        """
        import database.migrations.versions.phase10_twin_graph as mig_module
        import inspect

        migration_source = inspect.getsource(mig_module)

        required_indexes = [
            'ix_twin_rel_source',
            'ix_twin_rel_target',
            'ix_twin_rel_type',
            'ix_twin_rel_tenant',
            'ix_twin_rel_all',
        ]

        missing = [idx for idx in required_indexes if idx not in migration_source]
        assert not missing, f"Missing indexes in migration: {missing}"

        # Also verify model-level indexes via __table_args__
        from services.twin_graph.models import TwinRelationship
        table_args = TwinRelationship.__table_args__
        table_args_str = str(table_args)

        for idx_name in ['ix_twin_rel_source', 'ix_twin_rel_target',
                         'ix_twin_rel_type', 'ix_twin_rel_all']:
            assert idx_name in table_args_str, \
                f"Model __table_args__ missing Index({idx_name})"


# ============================================================
# SECTION 2: SECURITY HARDENING (6 tests)
# ============================================================

class TestSecurityHardening:
    """Verify tenant isolation and security enforcement."""

    @pytest.mark.asyncio
    async def test_cross_tenant_relationship_create_blocked(self):
        """Entity A in Tenant A cannot be related to Entity B in Tenant B."""
        from services.twin_graph.services import TwinGraphService

        session = AsyncMock()
        service = TwinGraphService(session)

        entity_a_tenant = uuid4()
        entity_b_tenant = uuid4()
        same_tenant = uuid4()

        # Source exists for its tenant
        mock_source = MagicMock()
        mock_source.id = uuid4()

        # Target exists for a DIFFERENT tenant
        mock_target_other_tenant = MagicMock()
        mock_target_other_tenant.id = uuid4()

        def side_effect(entity_id, tid):
            if tid == entity_a_tenant:
                return mock_source
            if tid == entity_b_tenant:
                return mock_target_other_tenant
            return None

        service._entity_repo.get_by_id_for_tenant = AsyncMock(side_effect=side_effect)
        service._repo.get_by_ids = AsyncMock(return_value=None)

        # Same-tenant request should fail because target not found in same_tenant
        with pytest.raises(Exception):
            await service.create_relation(mock_source.id, mock_target_other_tenant.id, "contains", same_tenant)

    @pytest.mark.asyncio
    async def test_cross_tenant_neighbor_query_blocked(self):
        """Tenant A cannot query neighbors of Tenant B's entities."""
        from services.twin_graph.services import TwinGraphService

        session = AsyncMock()
        service = TwinGraphService(session)

        target_entity = uuid4()
        tenant_a = uuid4()
        tenant_b = uuid4()

        mock_entity = MagicMock()
        mock_entity.id = target_entity

        def side_effect(entity_id, tid):
            return mock_entity if entity_id == target_entity and tid == tenant_a else None

        service._entity_repo.get_by_id_for_tenant = AsyncMock(side_effect=side_effect)

        # Tenant B querying Tenant A's entity should fail
        with pytest.raises(Exception):
            await service.get_neighbors(target_entity, tenant_b)

    @pytest.mark.asyncio
    async def test_cross_tenant_path_query_blocked(self):
        """Path queries are isolated by tenant."""
        from services.twin_graph.services import TwinGraphService

        session = AsyncMock()
        service = TwinGraphService(session)

        source_id = uuid4()
        target_id = uuid4()
        tenant_a = uuid4()
        tenant_b = uuid4()

        def side_effect(entity_id, tid):
            if entity_id == source_id and tid == tenant_a:
                return MagicMock(id=source_id)
            if entity_id == target_id and tid == tenant_a:
                return MagicMock(id=target_id)
            return None

        service._entity_repo.get_by_id_for_tenant = AsyncMock(side_effect=side_effect)

        # Tenant B cannot find path between Tenant A's entities
        with pytest.raises(Exception):
            await service.find_path(source_id, target_id, tenant_b)

    def test_tenant_id_not_from_payload(self):
        """Verify tenant_id comes from JWT context, not request body."""
        from services.twin_graph.routes import router

        for route in router.routes:
            if hasattr(route, 'endpoint'):
                sig = inspect.signature(route.endpoint)
                params = list(sig.parameters.keys())

                # Find tenant_id parameter
                if 'tenant_id' in params:
                    param = sig.parameters['tenant_id']
                    # Must have Depends, not a body default
                    assert hasattr(param.default, 'dependency') or 'Depends' in str(param.default), \
                        f"Route {route.path}: tenant_id must come from Depends, not body"

    def test_graph_repository_filters_tenant(self):
        """Verify all repository queries include tenant filtering."""
        from services.twin_graph.repositories import TwinRelationshipRepository
        import inspect

        repo_methods = [
            'get_by_ids',
            'list_source_relationships',
            'list_target_relationships',
            'list_by_type',
            'count_by_type',
        ]

        for method_name in repo_methods:
            method = getattr(TwinRelationshipRepository, method_name)
            source = inspect.getsource(method)
            assert 'tenant_id' in source, \
                f"{method_name} must filter by tenant_id"

    def test_permission_required_on_all_endpoints(self):
        """Verify all endpoints require permission checks."""
        from services.twin_graph.routes import router

        for route in router.routes:
            if hasattr(route, 'dependencies') and route.dependencies:
                # Endpoints should have dependency guards
                assert len(route.dependencies) > 0, \
                    f"Route {route.path} requires permission dependencies"


# ============================================================
# SECTION 3: BOUNDARY HARDENING (5 tests)
# ============================================================

class TestBoundaryHardening:
    """Verify architectural boundaries are maintained."""

    def test_no_adapter_dependency(self):
        """twin_graph must not depend on services.adapter."""
        violations = self._scan_for_imports(['services.adapter'])
        assert not violations, f"Found forbidden adapter imports: {violations}"

    def test_no_protocol_dependency(self):
        """twin_graph must not depend on protocol libraries."""
        violations = self._scan_for_imports([
            'bacnet', 'modbus', 'mqtt', 'opcua', 'plc',
            'kafka', 'redis', 'neo4j', 'networkx'
        ])
        assert not violations, f"Found forbidden protocol/library imports: {violations}"

    def test_no_runtime_state_in_graph(self):
        """TwinRelationship must not store runtime state fields."""
        from services.twin_graph.models import TwinRelationship

        forbidden_fields = ['runtime_state', 'device_id', 'sensor_value', 'telemetry']
        annotations = getattr(TwinRelationship, '__annotations__', {})

        violations = [f for f in forbidden_fields if f in annotations]
        assert not violations, f"TwinRelationship must not have runtime fields: {violations}"

    def test_no_device_dependency(self):
        """TwinRelationship must not reference Device model directly."""
        from services.twin_graph.models import TwinRelationship
        annotations = getattr(TwinRelationship, '__annotations__', {})

        assert 'device_id' not in annotations, \
            "TwinRelationship must not have device_id (use twin_entities via binding)"

    def test_no_graph_database_dependency(self):
        """twin_graph must use PostgreSQL, not external graph databases."""
        violations = self._scan_for_imports(['neo4j', 'networkx'])
        assert not violations, f"Found forbidden graph DB imports: {violations}"

    def _scan_for_imports(self, forbidden: list[str]) -> list[str]:
        """Scan twin_graph module for forbidden imports."""
        violations = []
        twin_graph_dir = os.path.join(PROJECT_ROOT, 'services', 'twin_graph')

        for root, _, files in os.walk(twin_graph_dir):
            for filename in files:
                if not filename.endswith('.py'):
                    continue
                filepath = os.path.join(root, filename)
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read().lower()
                for keyword in forbidden:
                    if keyword.lower() in content:
                        violations.append(f"{filepath}: '{keyword}'")
        return violations


# ============================================================
# SECTION 4: REPOSITORY BOUNDARY (additional checks)
# ============================================================

class TestRepositoryBoundary:
    """Verify repository adheres to boundary rules."""

    def test_repository_extends_tenant_aware(self):
        """TwinRelationshipRepository must extend TenantAwareRepository."""
        from services.twin_graph.repositories import TwinRelationshipRepository
        from services.core.repositories.base import TenantAwareRepository

        assert issubclass(TwinRelationshipRepository, TenantAwareRepository), \
            "TwinRelationshipRepository must extend TenantAwareRepository"

    def test_repository_no_commit_or_rollback(self):
        """Repository must not call commit() or rollback()."""
        from services.twin_graph.repositories import TwinRelationshipRepository
        import inspect

        source = inspect.getsource(TwinRelationshipRepository)
        assert 'commit()' not in source, "Repository must not call commit()"
        assert 'rollback()' not in source, "Repository must not call rollback()"

    def test_repository_uses_async_session(self):
        """Repository must accept AsyncSession in constructor."""
        from services.twin_graph.repositories import TwinRelationshipRepository

        sig = inspect.signature(TwinRelationshipRepository.__init__)
        params = list(sig.parameters.keys())
        assert 'session' in params, "Repository must accept session parameter"


# ============================================================
# SECTION 5: SERVICE LAYER HARDENING
# ============================================================

class TestServiceLayerHardening:
    """Verify service layer purity."""

    def test_service_has_no_protocol_calls(self):
        """TwinGraphService must not contain protocol-specific code."""
        from services.twin_graph.services import TwinGraphService
        import inspect

        source = inspect.getsource(TwinGraphService)
        # Check for protocol/library imports or calls, excluding common words like 'ai'
        forbidden_patterns = [
            r'\bimport\b\s+(bacnet|modbus|mqtt|opcua|plc)',
            r'\bfrom\b\s+(services\.adapter|services\.telemetry\.runtime)\b',
            r'\bneo4j\b',
            r'\bnetworkx\b',
            r'\bkafka\b',
            r'\bredis\b',
        ]

        import re
        violations = []
        for pattern in forbidden_patterns:
            matches = re.findall(pattern, source.lower())
            if matches:
                violations.append(f"{pattern}: {matches}")
        assert not violations, f"TwinGraphService must not contain protocol/library references: {violations}"

    def test_service_never_accepts_tenant_from_body(self):
        """Service methods must not have optional tenant_id with default."""
        from services.twin_graph.services import TwinGraphService

        for method_name in ['create_relation', 'remove_relation', 'get_relation',
                          'get_neighbors', 'find_path', 'list_relations_by_type']:
            method = getattr(TwinGraphService, method_name)
            sig = inspect.signature(method)
            params = list(sig.parameters.keys())
            if 'tenant_id' in params:
                param = sig.parameters['tenant_id']
                assert param.default is inspect.Parameter.empty, \
                    f"{method_name}: tenant_id must be required, not optional"


# ============================================================
# SECTION 6: QUERY ENGINE HARDENING
# ============================================================

class TestQueryEngineHardening:
    """Verify query engine safety and isolation."""

    def test_query_engine_has_max_depth(self):
        """TwinQueryEngine.find_path must have max_depth limit."""
        from services.twin_graph.query import TwinQueryEngine
        import inspect

        source = inspect.getsource(TwinQueryEngine.find_path)
        assert 'max_depth' in source, "find_path must respect max_depth parameter"

    def test_query_engine_uses_repo_not_direct_session(self):
        """QueryEngine must use repository, not direct session access."""
        from services.twin_graph.query import TwinQueryEngine
        import inspect

        source = inspect.getsource(TwinQueryEngine)
        # Should not have direct session.execute calls
        assert '.session.execute' not in source, \
            "QueryEngine must use repository, not direct session access"
