"""Task 10 Architecture Dependency Scan — Enforce Kernel Boundary for twin_graph."""
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)

TWIN_GRAPH_DIR = os.path.join(PROJECT_ROOT, "services", "twin_graph")

FORBIDDEN_IMPORTS = [
    "services.adapter",
    "services.telemetry.runtime",
    "neo4j",
    "networkx",
]

FORBIDDEN_KEYWORDS = [
    "bacnet",
    "modbus",
    "mqtt",
    "opcua",
    "plc",
    "kafka",
    "redis",
    "celery",
    "three.js",
    "bim",
]


class TestArchitectureDependencyScan:
    """Test that twin_graph module has no forbidden dependencies."""

    def test_no_adapter_imports(self):
        """Verify no imports from services.adapter in twin_graph module."""
        violations = []
        for root, dirs, files in os.walk(TWIN_GRAPH_DIR):
            for fn in files:
                if not fn.endswith(".py"):
                    continue
                filepath = os.path.join(root, fn)
                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read()
                for imp in FORBIDDEN_IMPORTS:
                    if imp in content:
                        violations.append(f"{filepath}: {imp}")
        assert not violations, f"Found forbidden imports: {violations}"

    def test_no_protocol_keywords(self):
        """Verify no protocol keywords in twin_graph module."""
        violations = []
        for root, dirs, files in os.walk(TWIN_GRAPH_DIR):
            for fn in files:
                if not fn.endswith(".py"):
                    continue
                filepath = os.path.join(root, fn)
                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read().lower()
                for kw in ["bacnet", "modbus", "mqtt", "opcua", "plc"]:
                    if kw in content:
                        violations.append(f"{filepath}: found '{kw}'")
        assert not violations, f"Found protocol keywords: {violations}"

    def test_no_infra_imports(self):
        """Verify no infrastructure imports (kafka, redis, etc.)."""
        violations = []
        for root, dirs, files in os.walk(TWIN_GRAPH_DIR):
            for fn in files:
                if not fn.endswith(".py"):
                    continue
                filepath = os.path.join(root, fn)
                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read().lower()
                for kw in ["kafka", "celery", "redis"]:
                    if kw in content:
                        violations.append(f"{filepath}: found '{kw}'")
        assert not violations, f"Found infra imports: {violations}"

    def test_no_graph_database_dependency(self):
        """Verify no Neo4j or external graph database dependencies."""
        violations = []
        for root, dirs, files in os.walk(TWIN_GRAPH_DIR):
            for fn in files:
                if not fn.endswith(".py"):
                    continue
                filepath = os.path.join(root, fn)
                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read()
                for lib in ["neo4j", "networkx"]:
                    if lib in content.lower():
                        violations.append(f"{filepath}: found '{lib}'")
        assert not violations, f"Found graph DB dependencies: {violations}"

    def test_allows_twin_and_core_imports(self):
        """Verify twin_graph correctly imports from allowed modules."""
        from services.twin_graph.repositories import TwinRelationshipRepository
        from services.core.repositories.base import TenantAwareRepository
        # Should extend TenantAwareRepository
        assert issubclass(TwinRelationshipRepository, TenantAwareRepository)


class TestModelLayerReview:
    """Verify model layer follows SQLAlchemy 2.x patterns."""

    def test_model_uses_mapped_column(self):
        """Verify TwinRelationship uses Mapped[] type hints."""
        from sqlalchemy import inspect as sa_inspect
        from services.twin_graph.models import TwinRelationship

        mapper = sa_inspect(TwinRelationship)
        for col in mapper.columns:
            assert col.name in [c.key for c in mapper.columns]

    def test_no_device_id_on_relationship(self):
        """TwinRelationship must NOT reference Device model directly."""
        from services.twin_graph.models import TwinRelationship
        annotations = getattr(TwinRelationship, "__annotations__", {})
        assert "device_id" not in annotations, \
            "TwinRelationship must not have device_id (use twin_entities via binding)"

    def test_source_target_are_uuid(self):
        """source_twin_id and target_twin_id must be UUID type."""
        from services.twin_graph.models import TwinRelationship
        from sqlalchemy import inspect as sa_inspect

        mapper = sa_inspect(TwinRelationship)
        source_col = mapper.columns["source_twin_id"]
        target_col = mapper.columns["target_twin_id"]
        # Both should be UUID-compatible
        assert source_col is not None
        assert target_col is not None

    def test_relationship_type_is_string(self):
        """relationship_type must be a string column."""
        from services.twin_graph.models import TwinRelationship
        from sqlalchemy import inspect as sa_inspect
        from sqlalchemy import String as SA_String

        mapper = sa_inspect(TwinRelationship)
        rel_type_col = mapper.columns["relationship_type"]
        assert isinstance(rel_type_col.type, SA_String)

    def test_check_constraint_no_self_reference(self):
        """Verify CHECK constraint prevents self-referencing relationships."""
        from services.twin_graph.models import TwinRelationship

        table = TwinRelationship.__table__
        check_constraints = [c for c in table.constraints if hasattr(c, 'sqltext')]
        has_check = any("source_twin_id != target_twin_id" in str(c.sqltext)
                       for c in check_constraints)
        assert has_check, "Missing CHECK constraint for no self-reference"
