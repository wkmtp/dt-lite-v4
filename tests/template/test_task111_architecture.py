"""Task 11.1 Architecture Hardening Review — Comprehensive audit of template module."""
import inspect
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)

TEMPLATE_DIR = os.path.join(PROJECT_ROOT, "services", "template")


# ===================================================================
# BOUNDARY TESTS (5)
# ===================================================================

class TestModuleBoundary:
    """Verify template module stays within extension-layer boundaries."""

    def test_no_forbidden_module_imports(self):
        """Template must not import from core kernel models directly."""
        forbidden_packages = [
            "services.twin.models",
            "services.twin.services",
            "services.twin_graph",
        ]
        violations = []
        for root, dirs, files in os.walk(TEMPLATE_DIR):
            for fn in files:
                if not fn.endswith(".py"):
                    continue
                filepath = os.path.join(root, fn)
                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read()
                for pkg in forbidden_packages:
                    if f"from {pkg}" in content or f"import {pkg}" in content:
                        violations.append(f"{filepath}: imports {pkg}")
        assert not violations, f"Forbidden imports found: {violations}"

    def test_no_protocol_keywords(self):
        """No protocol-specific keywords in template module."""
        forbidden = ["bacnet", "modbus", "opcua", "mqtt", "plc", "bim", "three"]
        violations = []
        for root, dirs, files in os.walk(TEMPLATE_DIR):
            for fn in files:
                if not fn.endswith(".py"):
                    continue
                filepath = os.path.join(root, fn)
                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read().lower()
                for kw in forbidden:
                    if kw in content:
                        violations.append(f"{filepath}: '{kw}'")
        assert not violations, f"Protocol keywords found: {violations}"

    def test_no_infra_keywords(self):
        """No infrastructure dependencies in template module."""
        forbidden = ["redis", "kafka", "celery", "neo4j", "networkx"]
        violations = []
        for root, dirs, files in os.walk(TEMPLATE_DIR):
            for fn in files:
                if not fn.endswith(".py"):
                    continue
                filepath = os.path.join(root, fn)
                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read().lower()
                for kw in forbidden:
                    if kw in content:
                        violations.append(f"{filepath}: '{kw}'")
        assert not violations, f"Infrastructure keywords found: {violations}"

    def test_allows_core_and_identity_imports(self):
        """Template may import from core base classes and identity auth deps."""
        from services.template.repositories import TemplateRepository
        from services.core.repositories.base import TenantAwareRepository
        assert issubclass(TemplateRepository, TenantAwareRepository)

        from services.auth.dependencies import get_current_tenant
        assert callable(get_current_tenant)

    def test_service_creates_no_entity(self):
        """Template service must never create TwinEntity instances."""
        from services.template.services import TemplateService
        source = inspect.getsource(TemplateService)
        assert "TwinEntity" not in source, "Service must not reference TwinEntity"
        assert "persistent_twin_entity" not in source.lower(), "Must not reference PersistentTwinEntity"


# ===================================================================
# SECURITY TESTS (5)
# ===================================================================

class TestTenantSecurity:
    """Verify tenant isolation enforcement in template module."""

    def test_tenant_id_not_from_request_body(self):
        """tenant_id must never be accepted from request body."""
        from services.template.schemas import TemplateCreateRequest
        fields = TemplateCreateRequest.model_fields
        assert "tenant_id" not in fields, \
            "TemplateCreateRequest must NOT accept tenant_id from client"

        from services.template.schemas import TemplateUpdateRequest
        fields = TemplateUpdateRequest.model_fields
        assert "tenant_id" not in fields, \
            "TemplateUpdateRequest must NOT accept tenant_id from client"

    def test_routes_use_get_current_tenant_dependency(self):
        """All route handlers must have get_current_tenant as a dependency param."""
        from services.template.routes import router
        import inspect

        # Get the actual function source for each route
        for route in router.routes:
            if hasattr(route, "endpoint"):
                src = inspect.getsource(route.endpoint)
                # Check either route-level dependencies OR function param dependency
                dep_str = str(route.dependencies)
                has_dep_in_params = "get_current_tenant" in src
                has_dep_in_list = "get_current_tenant" in dep_str
                assert has_dep_in_params or has_dep_in_list, \
                    f"Route {route.methods} {route.path} must use get_current_tenant"

    def test_permission_required_on_all_endpoints(self):
        """Every endpoint must require a permission."""
        from services.template.routes import router
        for route in router.routes:
            assert hasattr(route, "dependencies"), \
                f"Route {route.path} missing dependencies"
            assert len(route.dependencies) > 0, \
                f"Route {route.path} has no permission guards"
            dep_str = str(route.dependencies)
            assert "require_permission" in dep_str, \
                f"Route {route.path} must use require_permission"

    def test_repository_uses_tenant_filter(self):
        """All repository queries must include tenant_id filter."""
        from services.template.repositories import TemplateRepository
        methods = ["get_by_code", "list_active", "count_active"]
        for name in methods:
            method = getattr(TemplateRepository, name)
            src = inspect.getsource(method)
            assert "tenant_id" in src, f"{name} must filter by tenant_id"

    def test_create_template_uses_context_tenant(self):
        """create_template must receive tenant_id from context, not from request."""
        from services.template.services import TemplateService
        sig = inspect.signature(TemplateService.create_template)
        params = list(sig.parameters.keys())
        # tenant_id must be a separate parameter (not inside request)
        assert "tenant_id" in params, "create_template must have tenant_id parameter"
        # request must NOT contain tenant_id
        req_param = sig.parameters["request"]
        from services.template.schemas import TemplateCreateRequest
        assert req_param.annotation == TemplateCreateRequest, \
            "request param must be TemplateCreateRequest (which excludes tenant_id)"


# ===================================================================
# REPOSITORY TESTS (4)
# ===================================================================

class TestRepositoryBoundary:
    """Verify repository layer compliance."""

    def test_all_repos_extend_tenant_aware(self):
        """All template repositories must extend TenantAwareRepository."""
        from services.template.repositories import (
            TemplateRepository,
            TemplatePropertyRepository,
            TemplateRelationshipRepository,
        )
        from services.core.repositories.base import TenantAwareRepository
        assert issubclass(TemplateRepository, TenantAwareRepository)
        assert issubclass(TemplatePropertyRepository, TenantAwareRepository)
        assert issubclass(TemplateRelationshipRepository, TenantAwareRepository)

    def test_no_commit_in_repository(self):
        """Repositories must never call commit()."""
        from services.template.repositories import TemplateRepository
        source = inspect.getsource(TemplateRepository)
        assert ".commit()" not in source, "Repository must not call commit()"

    def test_no_rollback_in_repository(self):
        """Repositories must never call rollback()."""
        from services.template.repositories import TemplateRepository
        source = inspect.getsource(TemplateRepository)
        assert ".rollback()" not in source, "Repository must not call rollback()"

    def test_soft_delete_filter_in_queries(self):
        """All SELECT queries must exclude soft-deleted records."""
        from services.template.repositories import TemplateRepository
        for name in ["get_by_code", "list_active", "count_active"]:
            method = getattr(TemplateRepository, name)
            src = inspect.getsource(method)
            assert "deleted_at" in src, f"{name} must filter deleted_at"


# ===================================================================
# SCHEMA VALIDATION TESTS (4)
# ===================================================================

class TestSchemaValidation:
    """Verify schema_definition validation rules."""

    def test_valid_schema_accepted(self):
        """Valid schema should pass validation."""
        from services.template.services.schema_validator import SchemaValidator
        valid = {
            "version": "1.0",
            "properties": [
                {"name": "temperature", "data_type": "float", "unit": "celsius"},
                {"name": "status", "data_type": "string"},
            ],
        }
        errors = SchemaValidator.validate(valid)
        assert errors == [], f"Valid schema rejected: {errors}"

    def test_invalid_data_type_rejected(self):
        """Unknown data types must be rejected."""
        from services.template.services.schema_validator import SchemaValidator
        invalid = {
            "properties": [
                {"name": "value", "data_type": "superstring"},
            ],
        }
        errors = SchemaValidator.validate(invalid)
        assert len(errors) > 0, "Invalid data type must be rejected"
        assert "data_type" in errors[0].lower()

    def test_empty_property_name_rejected(self):
        """Properties with empty names must be rejected."""
        from services.template.services.schema_validator import SchemaValidator
        invalid = {
            "properties": [
                {"name": "", "data_type": "float"},
            ],
        }
        errors = SchemaValidator.validate(invalid)
        assert len(errors) > 0

    def test_missing_properties_key_rejected(self):
        """schema without 'properties' key must be rejected."""
        from services.template.services.schema_validator import SchemaValidator
        invalid = {"version": "1.0"}
        errors = SchemaValidator.validate(invalid)
        assert len(errors) > 0
        assert "properties" in errors[0].lower()


# ===================================================================
# MIGRATION TESTS (2)
# ===================================================================

class TestMigrationAudit:
    """Verify migration integrity."""

    def test_migration_revision_chain(self):
        """Migration must extend phase10_twin_graph."""
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "phase11",
            os.path.join(PROJECT_ROOT, "database", "migrations", "versions", "phase11_template_foundation.py"),
        )
        mig = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mig)
        assert mig.down_revision == "phase10_twin_graph", \
            f"Expected down_revision='phase10_twin_graph', got '{mig.down_revision}'"
        assert mig.revision == "phase11_template_foundation"

    def test_migration_creates_three_tables(self):
        """Migration must create twin_templates, template_properties, template_relationships."""
        mig_path = os.path.join(
            PROJECT_ROOT, "database", "migrations", "versions",
            "phase11_template_foundation.py"
        )
        with open(mig_path) as f:
            source = f.read()
        assert "twin_templates" in source
        assert "template_properties" in source
        assert "template_relationships" in source


# ===================================================================
# MODEL BOUNDARY TESTS (5)
# ===================================================================

class TestModelBoundary:
    """Verify model purity — no runtime/protocol fields."""

    def test_twin_template_has_no_device_field(self):
        """TwinTemplate must not have device-related fields."""
        from services.template.models import TwinTemplate
        annotations = TwinTemplate.__annotations__
        forbidden = ["device_id", "sensor_id", "protocol", "endpoint"]
        for field in forbidden:
            assert field not in annotations, f"TwinTemplate must not have '{field}'"

    def test_twin_template_has_no_runtime_state(self):
        """TwinTemplate must not store runtime state."""
        from services.template.models import TwinTemplate
        annotations = TwinTemplate.__annotations__
        forbidden = ["runtime_state", "current_value", "telemetry", "last_reading"]
        for field in forbidden:
            assert field not in annotations, f"TwinTemplate must not have '{field}'"

    def test_twin_template_uses_sqlalchemy_2x_style(self):
        """TwinTemplate must use Mapped[] and mapped_column()."""
        from services.template.models import TwinTemplate
        annotations = TwinTemplate.__annotations__
        assert "id" in annotations
        assert "Mapped" in str(annotations["id"]) or "mapped_column" in str(annotations["id"]), \
            "Must use SQLAlchemy 2.x style"

    def test_template_property_has_unique_constraint(self):
        """TemplateProperty must enforce unique(name) within template."""
        from services.template.models import TemplateProperty
        table = TemplateProperty.__table__
        unique_names = [c.name for c in table.constraints if hasattr(c, "columns")]
        assert "uq_prop_template_name" in unique_names

    def test_template_relationship_is_semantic_only(self):
        """TemplateRelationship must only define semantic relationships, no runtime edges."""
        from services.template.models import TemplateRelationship
        annotations = TemplateRelationship.__annotations__
        assert "relationship_type" in annotations
        assert "target_template" in annotations
        # Must NOT have fields that create runtime graph edges
        assert "source_twin_id" not in annotations
        assert "target_twin_id" not in annotations
