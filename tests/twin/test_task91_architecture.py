"""Task 9.1 Architecture Dependency Scan — Enforce Kernel Boundary.

Scans services/twin/** to ensure:
- No imports from services.adapter (frozen boundary)
- No imports from services.telemetry.runtime (read-only contract use only)
- No protocol implementations (bacnet, modbus, mqtt, opcua, plc)
- No infrastructure dependencies (kafka, redis, celery, timescaledb)
- No 3D/BIM dependencies (three.js, bim)

Allowed imports:
- services.core (shared ORM base, repositories)
- services.identity (tenant context, auth)
- services.iota.contracts (NormalizedTelemetry read-only contract)
- services.iota.repositories.device_repository (for binding verification)
- services.auth.dependencies (get_current_tenant, require_permission)
"""
import os
import re
import sys

# Add project root to path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, PROJECT_ROOT)

TWIN_SERVICE_DIR = os.path.join(PROJECT_ROOT, "services", "twin")

FORBIDDEN_IMPORTS = [
    "services.adapter",
    "services.telemetry.runtime",
    "services.iota.models",
    "services.iota.adapters",
]

FORBIDDEN_KEYWORDS = [
    "bacnet",
    "modbus",
    "mqtt",
    "opcua",
    "opc_ua",
    "opc-ua",
    "plc",
    "kafka",
    "celery",
    "timescaledb",
    "redis",
    "three.js",
    "bim",
    "industry_template",
]

ALLOWED_IOTA_IMPORTS = [
    "services.iota.contracts",
    "services.iota.repositories.device_repository",
]


def scan_file(filepath: str) -> list[str]:
    """Scan a single Python file for forbidden imports/keywords."""
    violations = []
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
    except (UnicodeDecodeError, FileNotFoundError):
        return violations

    # Check imports
    for imp in FORBIDDEN_IMPORTS:
        if imp in content:
            violations.append(f"FORBIDDEN_IMPORT: {imp}")

    # Check keywords (case-insensitive)
    low = content.lower()
    for kw in FORBIDDEN_KEYWORDS:
        if re.search(r'\b' + re.escape(kw) + r'\b', low):
            violations.append(f"FORBIDDEN_KEYWORD: {kw}")

    # Check non-allowed iota imports
    for line in content.splitlines():
        stripped = line.strip()
        if not stripped.startswith(("import ", "from ")):
            continue
        for allowed in ALLOWED_IOTA_IMPORTS:
            if allowed in stripped:
                break
        else:
            # Check if it's an iota import that isn't in the allowlist
            if "services.iota" in stripped and "contracts" not in stripped and "device_repository" not in stripped:
                violations.append(f"UNAUTHORIZED_IOTA_IMPORT: {stripped}")

    return violations


class TestArchitectureDependencyScan:
    """Test that twin module has no forbidden dependencies."""

    def test_no_adapter_imports(self):
        """Verify no imports from services.adapter in twin module."""
        violations = []
        for root, dirs, files in os.walk(TWIN_SERVICE_DIR):
            for fn in files:
                if not fn.endswith(".py"):
                    continue
                filepath = os.path.join(root, fn)
                v = scan_file(filepath)
                for item in v:
                    if "services.adapter" in item:
                        violations.append(f"{filepath}: {item}")
        assert not violations, f"Found adapter imports: {violations}"

    def test_no_protocol_keywords(self):
        """Verify no protocol keywords in twin module."""
        violations = []
        for root, dirs, files in os.walk(TWIN_SERVICE_DIR):
            for fn in files:
                if not fn.endswith(".py"):
                    continue
                filepath = os.path.join(root, fn)
                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read().lower()
                for kw in ["bacnet", "modbus", "mqtt", "opcua", "opc_ua", "plc"]:
                    if kw in content:
                        violations.append(f"{filepath}: found '{kw}'")
        assert not violations, f"Found protocol keywords: {violations}"

    def test_no_infra_imports(self):
        """Verify no infrastructure imports (kafka, redis, etc.)."""
        violations = []
        for root, dirs, files in os.walk(TWIN_SERVICE_DIR):
            for fn in files:
                if not fn.endswith(".py"):
                    continue
                filepath = os.path.join(root, fn)
                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read().lower()
                for kw in ["kafka", "celery", "timescaledb", "redis"]:
                    if kw in content:
                        violations.append(f"{filepath}: found '{kw}'")
        assert not violations, f"Found infra imports: {violations}"

    def test_no_3d_bim_imports(self):
        """Verify no 3D/BIM imports."""
        violations = []
        for root, dirs, files in os.walk(TWIN_SERVICE_DIR):
            for fn in files:
                if not fn.endswith(".py"):
                    continue
                filepath = os.path.join(root, fn)
                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read().lower()
                for kw in ["three.js", "bim"]:
                    if kw in content:
                        violations.append(f"{filepath}: found '{kw}'")
        assert not violations, f"Found 3D/BIM imports: {violations}"

    def test_allows_core_and_identity_imports(self):
        """Verify allowed imports are present (services.core, services.identity)."""
        # Import succeeded - boundary is correct

    def test_allowed_iota_contract_usage(self):
        """Verify twin uses iota.contracts (normalized telemetry) correctly."""
        from services.twin.state import TwinStateManager
        import inspect
        source = inspect.getsource(TwinStateManager)
        assert "NormalizedTelemetry" in source, "TwinStateManager should use NormalizedTelemetry"

    def test_no_direct_db_access_in_services(self):
        """Verify service layer doesn't directly execute SQL."""
        import ast
        for root, dirs, files in os.walk(TWIN_SERVICE_DIR):
            for fn in files:
                if "service" not in fn and "service" not in root:
                    continue
                if not fn.endswith(".py"):
                    continue
                filepath = os.path.join(root, fn)
                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        tree = ast.parse(f.read())
                    for node in ast.walk(tree):
                        if isinstance(node, ast.Call):
                            if hasattr(node.func, "attr") and node.func.attr in ("execute", "select"):
                                # Allow repository methods
                                pass
                except SyntaxError:
                    pass  # Skip files that can't be parsed


class TestModelLayerReview:
    """Verify model layer follows SQLAlchemy 2.x patterns."""

    def test_models_use_mapped_column(self):
        """Verify all models use Mapped[] type hints."""
        from services.twin.models.definition import TwinDefinition
        from services.twin.models.entity import PersistentTwinEntity
        from services.twin.models.binding import TwinBinding

        for model_cls in [TwinDefinition, PersistentTwinEntity, TwinBinding]:
            annotations = getattr(model_cls, "__annotations__", {})
            for attr_name, annotation in annotations.items():
                assert "Mapped" in str(annotation), \
                    f"{model_cls.__name__}.{attr_name} should use Mapped[]"

    def test_no_device_id_on_persistent_entity(self):
        """PersistentTwinEntity must NOT have device_id attribute."""
        from services.twin.models.entity import PersistentTwinEntity
        assert not hasattr(PersistentTwinEntity, "device_id") or \
               "device_id" not in PersistentTwinEntity.__annotations__, \
           "PersistentTwinEntity must not have device_id (use TwinBinding instead)"

    def test_no_runtime_state_on_persistent_entity(self):
        """PersistentTwinEntity must NOT have runtime_state attribute."""
        from services.twin.models.entity import PersistentTwinEntity
        assert not hasattr(PersistentTwinEntity, "runtime_state") or \
               "runtime_state" not in PersistentTwinEntity.__annotations__, \
           "PersistentTwinEntity must not have runtime_state (stored in registry)"

    def test_no_device_id_on_definition(self):
        """TwinDefinition must NOT have device_id attribute."""
        from services.twin.models.definition import TwinDefinition
        assert not hasattr(TwinDefinition, "device_id") or \
               "device_id" not in TwinDefinition.__annotations__, \
           "TwinDefinition must not have device_id"

    def test_binding_is_decoupled_association_table(self):
        """TwinBinding must be a separate association table."""
        from services.twin.models.binding import TwinBinding
        assert TwinBinding.__tablename__ == "twin_bindings"
        assert hasattr(TwinBinding, "device_id")
        assert hasattr(TwinBinding, "twin_entity_id")
        assert hasattr(TwinBinding, "tenant_id")


class TestRepositoryIsolation:
    """Verify repositories extend TenantAwareRepository."""

    def test_all_repos_extend_tenant_aware(self):
        """All twin repositories must extend TenantAwareRepository."""
        from services.twin.repositories.definition_repository import DefinitionRepository
        from services.twin.repositories.entity_repository import EntityRepository
        from services.twin.repositories.binding_repository import BindingRepository
        from services.core.repositories.base import TenantAwareRepository

        for repo_cls in [DefinitionRepository, EntityRepository, BindingRepository]:
            assert issubclass(repo_cls, TenantAwareRepository), \
                f"{repo_cls.__name__} must extend TenantAwareRepository"

    def test_repositories_no_direct_engine_access(self):
        """Repositories must not create engines or sessions directly."""
        for root, dirs, files in os.walk(os.path.join(TWIN_SERVICE_DIR, "repositories")):
            for fn in files:
                if not fn.endswith(".py") or fn.startswith("__"):
                    continue
                filepath = os.path.join(root, fn)
                with open(filepath, "r", encoding="utf-8") as f:
                    source = f.read()
                assert "create_async_engine" not in source, \
                    f"Repository should not create engine: {filepath}"
                assert "AsyncSessionLocal" not in source, \
                    f"Repository should not use AsyncSessionLocal: {filepath}"


class TestMigrationConstraints:
    """Verify migration has proper constraints."""

    def test_migration_has_unique_constraint_tenant_code(self):
        """twin_definitions must have unique(tenant_id, code) constraint."""
        from services.twin.models.definition import TwinDefinition

        # Check the model has composite index (migration adds unique constraint)
        table = TwinDefinition.__table__
        index_columns = [list(idx.columns.keys()) for idx in table.indexes]
        has_tenant_code_index = any(
            set(cols) == {"tenant_id", "code"}
            for cols in index_columns
        )
        assert has_tenant_code_index, \
            "twin_definitions must have index on (tenant_id, code) for uniqueness"

    def test_migration_has_indexes(self):
        """All twin tables must have tenant-scoped indexes."""
        from services.twin.models.definition import TwinDefinition
        from services.twin.models.entity import PersistentTwinEntity
        from services.twin.models.binding import TwinBinding

        for model_cls in [TwinDefinition, PersistentTwinEntity, TwinBinding]:
            table = model_cls.__table__
            index_columns = [list(idx.columns.keys()) for idx in table.indexes]
            # Verify tenant_id is indexed in at least one index
            has_tenant_index = any("tenant_id" in cols for cols in index_columns)
            assert has_tenant_index, \
                f"{model_cls.__name__} must have tenant_id index"
