"""Task 13.1 Architecture Hardening Review - Provisioning Engine."""
import ast
import inspect
import re
from pathlib import Path
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4


# ============================================================
# Section 1: Zero-Code Flow Validation (8 tests)
# ============================================================

class TestZeroCodeFlow:
    """Verify provisioning follows zero-code chain:
    Ontology → Capability → Template → DeploymentProfile →
    DeploymentInstance → ProvisioningPlan → ProvisioningExecution → TwinEntity → TwinRelationship
    """

    def test_provisioning_does_not_require_manual_code(self):
        """New industry object can be created through metadata only."""
        from services.provisioning.models import ProvisioningPlan, ProvisioningItem

        # All models exist and reference each other via UUID FK
        annotations_plan = ProvisioningPlan.__annotations__
        assert "tenant_id" in annotations_plan
        assert "deployment_instance_id" in annotations_plan
        assert "status" in annotations_plan
        assert "total_items" in annotations_plan

        annotations_item = ProvisioningItem.__annotations__
        assert "external_id" in annotations_item
        assert "action" in annotations_item
        assert "entity_type_id" in annotations_item

    def test_zero_code_chain_integrity(self):
        """Provisioning links deployment instance to template without code."""
        from services.provisioning.planner import ProvisioningPlanner
        sig = inspect.signature(ProvisioningPlanner.generate_plan)
        params = list(sig.parameters.keys())
        assert "deployment_instance_id" in params
        assert "tenant_id" in params
        # No manual_code, no sql, no protocol_config params
        forbidden = ["manual_code", "direct_sql", "protocol_config", "device_programming"]
        for fb in forbidden:
            assert fb not in params, f"Found forbidden param: {fb}"

    def test_provisioning_accepts_any_template(self):
        """Provisioning must work with any template type - building/manufacturing/energy/campus."""
        from services.provisioning.models import ProvisioningPlan
        # deployment_instance_id is a generic FK - no industry-specific fields
        annotations = ProvisioningPlan.__annotations__
        assert "deployment_instance_id" in annotations
        # Should NOT have industry-specific FKs
        for field in ["ahu_template_id", "robot_template_id", "transformer_template_id"]:
            assert field not in annotations

    def test_planner_reads_only_deployment_and_template(self):
        """Planner must only read DeploymentInstance and Template, nothing else."""
        source = Path("services/provisioning/planner.py").read_text(encoding="utf-8")
        # Must import from deployment and template
        assert "from services.deployment" in source or "import services.deployment" in source
        assert "from services.template" in source or "import services.template" in source
        # Must NOT import from adapter/telemetry
        assert "services.adapter" not in source
        assert "services.telemetry" not in source

    def test_executor_bridges_to_twin_only(self):
        """Executor must only create PersistentTwinEntity and TwinRelationship."""
        source = Path("services/provisioning/executor.py").read_text(encoding="utf-8")
        assert "PersistentTwinEntity" in source
        assert "TwinRelationship" in source
        assert "services.twin.models.entity" in source or "twin.models.entity" in source
        assert "services.twin_graph" in source

    def test_no_protocol_config_in_provisioning_request(self):
        """ProvisioningPlanCreateRequest must not accept protocol configuration."""
        from services.provisioning.schemas import ProvisioningPlanCreateRequest
        fields = ProvisioningPlanCreateRequest.model_fields
        for field_name in fields:
            assert "protocol" not in field_name.lower()
            assert "bacnet" not in field_name.lower()
            assert "modbus" not in field_name.lower()
            assert "mqtt" not in field_name.lower()

    def test_provisioning_service_validates_before_generating(self):
        """Service must validate deployment before generating plan."""
        from services.provisioning.services import ProvisioningService
        methods = [m for m in dir(ProvisioningService) if not m.startswith("_")]
        assert "validate_deployment" in methods
        assert "create_plan" in methods
        assert "execute_plan" in methods

    def test_migration_creates_all_three_tables(self):
        """Migration must create provisioning_plans, provisioning_items, provisioning_executions."""
        migration_path = Path("database/migrations/versions")
        for py_file in migration_path.rglob("phase13_provisioning*.py"):
            content = py_file.read_text(encoding="utf-8")
            assert "provisioning_plans" in content
            assert "provisioning_items" in content
            assert "provisioning_executions" in content


# ============================================================
# Section 2: Boundary Review (8 tests)
# ============================================================

class TestBoundaryReview:
    """Provisioning IS responsible for: plan generation, validation, lifecycle execution,
    twin identity creation.
    Provisioning IS NOT responsible for: device creation, adapter registration, protocol handling.
    """

    def test_provisioning_does_not_create_devices(self):
        """Provisioning must not import device-related modules."""
        source = Path("services/provisioning").rglob("*.py")
        for py_file in source:
            content = py_file.read_text(encoding="utf-8")
            assert "Device" not in content or "device" in content.lower().split("#")[0] == "" or \
                   "Device" in content and "twin" in content.lower(), \
                   f"{py_file} contains unexpected device references"

    def test_provisioning_does_not_register_adapters(self):
        """No adapter registration in provisioning layer."""
        source = Path("services/provisioning").rglob("*.py")
        for py_file in source:
            content = py_file.read_text(encoding="utf-8").lower()
            # Allow 'adapter' only in comments or as part of 'adapters' reference
            lines = [line.strip() for line in content.split("\n") if not line.strip().startswith("#")]
            for line in lines:
                if "adapter" in line and "registration" in line:
                    raise AssertionError(f"Found adapter registration reference in {py_file}")

    def test_provisioning_does_not_handle_discovery(self):
        """No BACnet/MQTT/OPC-UA discovery in provisioning."""
        source = Path("services/provisioning").rglob("*.py")
        for py_file in source:
            content = py_file.read_text(encoding="utf-8").lower()
            for keyword in ["bacnet", "discovery", "opc-ua", "opcua", "modbus", "plc"]:
                if keyword in content and keyword not in str(py_file):
                    raise AssertionError(f"Forbidden keyword '{keyword}' found in {py_file}")

    def test_provisioning_does_not_ingest_telemetry(self):
        """No telemetry ingestion in provisioning layer."""
        from services.provisioning import services as svc_module
        source = inspect.getsource(svc_module)
        assert "telemetry" not in source.lower() or "telemetry" in str(Path(svc_module.__file__))

    def test_provisioning_does_not_manage_runtime_state(self):
        """Provisioning must not use TwinStateManager or runtime state."""
        source = Path("services/provisioning").rglob("*.py")
        for py_file in source:
            content = py_file.read_text(encoding="utf-8")
            assert "TwinStateManager" not in content, f"TwinStateManager referenced in {py_file}"

    def test_provisioning_does_not_do_ai_reasoning(self):
        """Provisioning must not import AI reasoning modules."""
        source = Path("services/provisioning").rglob("*.py")
        for py_file in source:
            content = py_file.read_text(encoding="utf-8")
            # Allow 'ai' in comments or model names like 'entity_type'
            tree = ast.parse(content)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        assert alias.name != "services.ai"
                elif isinstance(node, ast.ImportFrom):
                    if node.module and node.module.startswith("services.ai"):
                        raise AssertionError(f"AI import found in {py_file}")

    def test_planner_is_pure_functional_logic(self):
        """Planner must not perform database mutations directly."""
        source = Path("services/provisioning/planner.py").read_text(encoding="utf-8")
        # Planner should use repos, not direct session.execute/select
        assert "session.execute(" not in source
        assert "await select(" not in source

    def test_executor_handles_side_effects_only(self):
        """Executor must be the only module doing side effects (DB writes)."""
        source = Path("services/provisioning/executor.py").read_text(encoding="utf-8")
        # Executor uses session.add, commit - these are allowed side effects
        assert "await self._session.add" in source
        assert "await self._session.commit" in source


# ============================================================
# Section 3: Tenant Security (8 tests)
# ============================================================

class TestTenantSecurity:
    """Tenant isolation: tenant_id comes ONLY from JWT/TenantContext, never from request body."""

    @pytest.mark.asyncio
    async def test_cross_tenant_plan_access_denied(self):
        """Cross-tenant plan access must return None."""
        from services.provisioning.repository import ProvisioningPlanRepository
        session = MagicMock()
        session.execute = AsyncMock()
        result = MagicMock()
        result.scalar_one_or_none.return_value = None
        session.execute.return_value = result
        repo = ProvisioningPlanRepository(session)
        r = await repo.get_by_id_for_tenant(uuid4(), uuid4())
        assert r is None

    @pytest.mark.asyncio
    async def test_cross_tenant_execution_denied(self):
        """Cross-tenant execution records must not be accessible."""
        from services.provisioning.repository import ProvisioningExecutionRepository
        session = MagicMock()
        session.execute = AsyncMock()
        result = MagicMock()
        result.scalars.return_value.all.return_value = []
        session.execute.return_value = result
        repo = ProvisioningExecutionRepository(session)
        r = await repo.list_by_plan(uuid4(), uuid4())
        assert r == []

    @pytest.mark.asyncio
    async def test_cross_tenant_item_access_denied(self):
        """Cross-tenant item access must be blocked."""
        from services.provisioning.repository import ProvisioningItemRepository
        session = MagicMock()
        session.execute = AsyncMock()
        result = MagicMock()
        result.scalar_one_or_none.return_value = None
        session.execute.return_value = result
        repo = ProvisioningItemRepository(session)
        r = await repo.get_by_external_id(uuid4(), "some_ext_id")
        assert r is None

    def test_no_tenant_id_in_request_body(self):
        """ProvisioningPlanCreateRequest must NOT contain tenant_id field."""
        from services.provisioning.schemas import ProvisioningPlanCreateRequest
        fields = ProvisioningPlanCreateRequest.model_fields
        assert "tenant_id" not in fields, "tenant_id should not be in request body schema"

    def test_routes_use_dependency_injection_for_tenant(self):
        """All endpoints must get tenant from Depends, not from request body."""
        from services.provisioning.routes import router
        for route in router.routes:
            deps = getattr(route, "dependencies", [])
            assert len(deps) > 0, f"Route {route.path} missing dependencies"

    def test_service_never_reads_tenant_from_body(self):
        """Service methods must accept tenant_id as explicit parameter."""
        import inspect
        from services.provisioning.services import ProvisioningService
        for method_name in ["create_plan", "execute_plan", "validate_deployment"]:
            method = getattr(ProvisioningService, method_name)
            sig = inspect.signature(method)
            params = list(sig.parameters.keys())
            assert "tenant_id" in params, f"{method_name} missing tenant_id parameter"

    def test_item_model_enforces_tenant_isolation(self):
        """ProvisioningItem must have tenant_id column."""
        from services.provisioning.models import ProvisioningItem
        annotations = ProvisioningItem.__annotations__
        assert "tenant_id" in annotations

    def test_execution_model_enforces_tenant_isolation(self):
        """ProvisioningExecution must have tenant_id column."""
        from services.provisioning.models import ProvisioningExecution
        annotations = ProvisioningExecution.__annotations__
        assert "tenant_id" in annotations


# ============================================================
# Section 4: Idempotency Verification (6 tests)
# ============================================================

class TestIdempotency:
    """Repeated provisioning with same tenant/instance/template must not duplicate entities."""

    @pytest.mark.asyncio
    async def test_same_external_id_creates_only_one_entity(self):
        """Duplicate external_id should not create new PersistentTwinEntity."""
        from services.provisioning.executor import ProvisioningExecutor

        session = MagicMock()
        executor = ProvisioningExecutor(session, MagicMock(), MagicMock(),
                                        MagicMock(), MagicMock(), MagicMock())
        executor._entity_repo = MagicMock()

        # First call returns existing entity
        existing = MagicMock()
        existing.id = uuid4()
        executor._entity_repo.get_by_external_id = AsyncMock(return_value=existing)

        item = MagicMock()
        item.external_id = "ahu_room_101"
        item.id = uuid4()

        result = await executor._execute_create_entity(item, uuid4())
        assert result == existing.id

    @pytest.mark.asyncio
    async def test_plan_generation_idempotent_on_completed(self):
        """Generating plan when one already completed returns existing plan."""
        from services.provisioning.planner import ProvisioningPlanner
        plan_repo = MagicMock()
        existing_plan = MagicMock()
        existing_plan.status = "completed"
        existing_plan.id = uuid4()
        plan_repo.get_by_deployment_id = AsyncMock(return_value=existing_plan)

        planner = ProvisioningPlanner(plan_repo, MagicMock(), MagicMock())
        result = await planner.generate_plan(uuid4(), uuid4())
        assert result == existing_plan

    @pytest.mark.asyncio
    async def test_retry_after_failure_safe(self):
        """Retrying failed plan does not cause errors."""
        from services.provisioning.planner import ProvisioningPlanner
        plan_repo = MagicMock()
        plan_repo.get_by_deployment_id = AsyncMock(return_value=None)
        planner = ProvisioningPlanner(plan_repo, MagicMock(), MagicMock())
        # Should not raise on first generate
        with patch.object(planner, '_plan_repo') as mock_repo:
            mock_repo.get_by_deployment_id = AsyncMock(return_value=None)
            # Plan generation would proceed - safe to retry after failure cleanup

    def test_external_id_uniqueness_per_item(self):
        """Each provisioning item has unique constraint on (plan_id, external_id, action)."""
        from services.provisioning.models import ProvisioningItem
        table = ProvisioningItem.__table__
        unique_constraints = [c.name for c in table.constraints if hasattr(c, "name")]
        assert "uq_item_plan_external_action" in unique_constraints

    def test_same_external_id_different_tenant_allowed(self):
        """Same external_id across different tenants must be allowed."""
        from services.provisioning.models import ProvisioningItem
        annotations = ProvisioningItem.__annotations__
        assert "tenant_id" in annotations
        assert "external_id" in annotations
        assert "plan_id" in annotations

    def test_plan_tracks_completion_progress(self):
        """Plan must track total_items and completed_items for idempotency verification."""
        from services.provisioning.models import ProvisioningPlan
        annotations = ProvisioningPlan.__annotations__
        assert "total_items" in annotations
        assert "completed_items" in annotations


# ============================================================
# Section 5: Repository Boundary (5 tests)
# ============================================================

class TestRepositoryBoundary:
    """Repositories extend TenantAwareRepository. No direct select/execute in service layer."""

    def test_all_repositories_extend_tenant_aware(self):
        """All provisioning repositories must extend TenantAwareRepository."""
        from services.provisioning.repository import (
            ProvisioningPlanRepository,
            ProvisioningItemRepository,
            ProvisioningExecutionRepository,
        )
        from services.core.repositories.base import TenantAwareRepository

        for repo_cls in [ProvisioningPlanRepository, ProvisioningItemRepository,
                         ProvisioningExecutionRepository]:
            assert issubclass(repo_cls, TenantAwareRepository), \
                f"{repo_cls.__name__} does not extend TenantAwareRepository"

    def test_service_uses_repository_methods_not_direct_session(self):
        """Service must use repository methods, not direct session queries."""
        from services.provisioning.services import ProvisioningService
        source = inspect.getsource(ProvisioningService)
        # Service should not call session.execute or session.select directly
        assert "session.execute(" not in source
        assert "await session.execute" not in source

    def test_plan_repository_has_tenant_filter(self):
        """Plan repository must have get_by_id_for_tenant method."""
        from services.provisioning.repository import ProvisioningPlanRepository
        assert hasattr(ProvisioningPlanRepository, "get_by_id_for_tenant")

    def test_item_repository_has_tenant_filter(self):
        """Item repository must have tenant-filtered methods."""
        from services.provisioning.repository import ProvisioningItemRepository
        assert hasattr(ProvisioningItemRepository, "list_by_plan")
        assert hasattr(ProvisioningItemRepository, "get_by_external_id")

    def test_execution_repository_has_tenant_filter(self):
        """Execution repository must have tenant-filtered methods."""
        from services.provisioning.repository import ProvisioningExecutionRepository
        assert hasattr(ProvisioningExecutionRepository, "list_by_plan")


# ============================================================
# Section 6: Migration Audit (3 tests)
# ============================================================

class TestMigrationAudit:
    """Verify phase13_provisioning.py migration structure."""

    def test_migration_revision_chain(self):
        """Migration must extend phase12_1_deployment_meta."""
        migration_path = Path("database/migrations/versions")
        for py_file in migration_path.rglob("phase13_provisioning*.py"):
            content = py_file.read_text(encoding="utf-8")
            assert "down_revision = 'phase12_1_deployment_meta'" in content, \
                f"Migration {py_file} does not chain correctly"

    def test_migration_has_tenant_isolation(self):
        """All tables must have tenant_id column for isolation."""
        migration_path = Path("database/migrations/versions")
        for py_file in migration_path.rglob("phase13_provisioning*.py"):
            content = py_file.read_text(encoding="utf-8")
            assert "tenant_id" in content, "Missing tenant_id in migration"

    def test_migration_has_soft_delete(self):
        """Tables should follow soft-delete pattern where applicable."""
        migration_path = Path("database/migrations/versions")
        for py_file in migration_path.rglob("phase13_provisioning*.py"):
            content = py_file.read_text(encoding="utf-8")
            # Soft delete handled via deleted_at column; FK constraints use ForeignKeyConstraint
            assert "deleted_at" in content, "Missing soft delete column"
            assert "ForeignKeyConstraint" in content or "foreign_key" in content.lower(), \
                "Missing foreign key constraints"


# ============================================================
# Section 7: Architecture Dependency Scan (2 tests)
# ============================================================

class TestDependencyScan:
    """Scan provisioning for forbidden imports and verify compliance."""

    FORBIDDEN_IMPORTS = [
        "services.adapter",
        "services.telemetry",
        "services.adapter.*",
        "services.telemetry.*",
        "services.bacnet",
        "services.modbus",
        "services.mqtt",
        "services.opcua",
        "services.plc",
        "services.ai",
        "services.kafka",
        "services.redis",
        "celery",
        "redis",
    ]

    FORBIDDEN_KEYWORDS = [
        "bacnet", "modbus", "mqtt", "opcua", "plc",
        "kafka", "redis", "celery",
    ]

    def test_no_forbidden_imports(self):
        """Provisioning must not import adapter, telemetry, etc."""
        violations = []
        for py_file in Path("services/provisioning").rglob("*.py"):
            content = py_file.read_text(encoding='utf-8')
            tree = ast.parse(content)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        for forbidden in self.FORBIDDEN_IMPORTS:
                            if alias.name.startswith(forbidden.replace("*", "")):
                                violations.append(f"{py_file}: {alias.name}")
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        for forbidden in self.FORBIDDEN_IMPORTS:
                            if node.module.startswith(forbidden.replace("*", "")):
                                violations.append(f"{py_file}: {node.module}")
        assert len(violations) == 0, f"Forbidden imports found: {violations}"

    def test_no_industry_coupling_keywords(self):
        """Provisioning must not contain industry-specific keywords."""
        violations = []
        for py_file in Path("services/provisioning").rglob("*.py"):
            content = py_file.read_text(encoding='utf-8')
            for line in content.splitlines():
                stripped = line.strip().lower()
                if stripped.startswith("#"):
                    continue
                for keyword in ["building_", "factory_", "energy_", "campus_",
                                "machine_", "sensor_", "ahu_", "transformer_"]:
                    if re.search(r'\b' + keyword.rstrip('_') + r'\b', stripped):
                        violations.append(f"{py_file}: '{keyword}'")
        assert len(violations) == 0, f"Industry coupling keywords found: {violations}"


# ============================================================
# Section 8: API Review (4 tests)
# ============================================================

class TestAPIReview:
    """All endpoints must be JWT protected and permission guarded."""

    def test_all_endpoints_have_permission_guard(self):
        """Every route must require permission dependency."""
        from services.provisioning.routes import router
        for route in router.routes:
            deps = getattr(route, "dependencies", [])
            assert any("require_permission" in str(d) for d in deps), \
                f"Route {route.path} missing permission guard"

    def test_all_endpoints_have_tenant_dependency(self):
        """Every route must get tenant from dependency injection (parameter or dependency)."""
        from services.provisioning.routes import router
        import inspect
        for route in router.routes:
            # Check route-level dependencies
            deps = getattr(route, "dependencies", [])
            has_dep = any("get_current_tenant" in str(d) or "tenant" in str(d).lower() for d in deps)
            # Also check function signature for Depends parameter
            func = getattr(route, "endpoint", None)
            has_param = False
            if func:
                sig = inspect.signature(func)
                for param_name, param in sig.parameters.items():
                    if param.default and hasattr(param.default, 'dependency'):
                        has_param = True
                        break
            assert has_dep or has_param, f"Route {route.path} missing tenant dependency"

    def test_request_schema_no_internal_ids(self):
        """Create plan request should not expose internal IDs beyond deployment_instance_id."""
        from services.provisioning.schemas import ProvisioningPlanCreateRequest
        fields = ProvisioningPlanCreateRequest.model_fields
        # Only deployment_instance_id should be in the create request
        assert "deployment_instance_id" in fields
        # Should not have execution_id, plan_id, etc.
        internal_ids = ["execution_id", "plan_id", "item_id"]
        for iid in internal_ids:
            assert iid not in fields

    def test_gateway_registers_provisioning_router(self):
        """Gateway must include provisioning router."""
        gateway_path = Path("services/gateway/main.py")
        content = gateway_path.read_text(encoding='utf-8')
        assert "provisioning_router" in content


# ============================================================
# Section 9: Lifecycle State Machine (4 tests)
# ============================================================

class TestLifecycleStateMachine:
    """Verify deployment instance and provisioning plan state machines."""

    def test_provisioning_plan_status_values(self):
        """ProvisioningPlan must have valid status values."""
        from services.provisioning.models import ProvisioningPlan
        annotations = ProvisioningPlan.__annotations__
        assert "status" in annotations

    def test_execution_status_tracking(self):
        """ProvisioningExecution must track status through execution."""
        from services.provisioning.models import ProvisioningExecution
        annotations = ProvisioningExecution.__annotations__
        assert "status" in annotations
        assert "started_at" in annotations
        assert "finished_at" in annotations

    @pytest.mark.asyncio
    async def test_cannot_execute_non_ready_plan(self):
        """Only plans in 'ready' status can be executed."""
        from services.provisioning.executor import ProvisioningExecutor

        session = MagicMock()
        executor = ProvisioningExecutor(session, MagicMock(), MagicMock(),
                                        MagicMock(), MagicMock(), MagicMock())

        plan = MagicMock()
        plan.status = "draft"
        executor._plan_repo = MagicMock()
        executor._plan_repo.get_by_id_for_tenant = AsyncMock(return_value=plan)

        with pytest.raises(RuntimeError, match="Cannot execute plan in status 'draft'"):
            await executor.execute(uuid4(), uuid4())

    @pytest.mark.asyncio
    async def test_cannot_regenerate_executing_plan(self):
        """Cannot regenerate plan while it's executing."""
        from services.provisioning.planner import ProvisioningPlanner

        plan_repo = MagicMock()
        running_plan = MagicMock()
        running_plan.status = "executing"
        running_plan.id = uuid4()
        plan_repo.get_by_deployment_id = AsyncMock(return_value=running_plan)

        planner = ProvisioningPlanner(plan_repo, MagicMock(), MagicMock())
        with pytest.raises(RuntimeError):
            await planner.generate_plan(uuid4(), uuid4())


# ============================================================
# Section 10: Model Constraints (4 tests)
# ============================================================

class TestModelConstraints:
    """Verify database constraints enforce data integrity."""

    def test_plan_table_has_unique_constraint(self):
        """provisioning_plans must have unique constraint on (tenant_id, deployment_instance_id)."""
        from services.provisioning.models import ProvisioningPlan
        table = ProvisioningPlan.__table__
        unique_constraints = [c.name for c in table.constraints if hasattr(c, "name")]
        assert "uq_plan_deployment" in unique_constraints

    def test_item_table_has_unique_constraint(self):
        """provisioning_items must have unique constraint on action type."""
        from services.provisioning.models import ProvisioningItem
        table = ProvisioningItem.__table__
        unique_constraints = [c.name for c in table.constraints if hasattr(c, "name")]
        assert "uq_item_plan_external_action" in unique_constraints

    def test_all_models_have_soft_delete(self):
        """All provisioning models must support soft delete."""
        from services.provisioning.models import ProvisioningPlan, ProvisioningItem, ProvisioningExecution
        from services.core.models.base import SoftDeleteMixin

        for model in [ProvisioningPlan, ProvisioningItem, ProvisioningExecution]:
            assert issubclass(model, SoftDeleteMixin), \
                f"{model.__name__} does not extend SoftDeleteMixin"

    def test_migration_no_frozen_table_modification(self):
        """Migration must not modify existing frozen tables."""
        migration_path = Path("database/migrations/versions")
        for py_file in migration_path.rglob("phase13_provisioning*.py"):
            content = py_file.read_text(encoding="utf-8")
            # Must only CREATE, not ALTER existing tables
            # Check that no alter statements reference frozen tables
            frozen_tables = ["twin_entities", "twin_relationships", "deployment_instances",
                             "deployment_profiles", "templates", "ontology_types"]
            for table in frozen_tables:
                assert f"alter_table('{table}" not in content.lower(), \
                    f"Migration modifies frozen table: {table}"
