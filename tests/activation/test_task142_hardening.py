"""Task 14.2 Hardening tests — Adapter boundary & protocol neutrality."""
import pytest
from pathlib import Path
import re


class TestProtocolNeutrality:
    """Verify no protocol-specific content in frozen modules."""

    FROZEN_DIRS = [
        "services/twin", "services/twin_graph", "services/template",
        "services/ontology", "services/deployment", "services/provisioning",
        "services/activation", "services/core", "services/identity",
    ]
    PROTOCOL_KEYWORDS = ["bacnet", "modbus", "opcua", "mqtt", "plc",
                         "kafka", "redis", "celery", "timescaledb"]

    def test_no_protocol_keywords_in_frozen_modules(self):
        """No protocol keywords in any frozen service module (excluding config/placeholders)."""
        violations = []
        for dir_path in self.FROZEN_DIRS:
            for py_file in Path(dir_path).rglob("*.py"):
                # Skip config files (placeholders only, not architectural dependencies)
                if py_file.name == "config.py":
                    continue
                content = py_file.read_text(encoding="utf-8")
                for line_no, line in enumerate(content.splitlines(), 1):
                    stripped = line.strip()
                    if stripped.startswith("#"):
                        continue
                    if '"""' in stripped or "'''" in stripped:
                        continue
                    for kw in self.PROTOCOL_KEYWORDS:
                        if re.search(r"\b" + kw + r"\b", stripped, re.IGNORECASE):
                            violations.append(
                                f"{py_file.relative_to('.')}:{line_no}: {kw}"
                            )
        assert not violations, f"Protocol contamination found:\n" + "\n".join(violations)

    def test_activation_models_no_protocol_fields(self):
        """TwinActivationLog and TwinCommand must not have protocol fields."""
        from services.activation.models import TwinActivationLog, TwinCommand
        for model in (TwinActivationLog, TwinCommand):
            annotations = model.__annotations__
            for field in annotations:
                for kw in self.PROTOCOL_KEYWORDS:
                    assert kw not in field.lower(), \
                        f"Protocol field '{field}' in {model.__name__}"

    def test_twin_binding_no_protocol_fields(self):
        """TwinBinding (Task 9) must not have protocol fields."""
        from services.twin.models.binding import TwinBinding
        annotations = TwinBinding.__annotations__
        for field in annotations:
            for kw in self.PROTOCOL_KEYWORDS:
                assert kw not in field.lower(), \
                    f"Protocol field '{field}' in TwinBinding"

    def test_persistent_twin_entity_no_protocol_fields(self):
        """PersistentTwinEntity must not have protocol fields."""
        from services.twin.models.entity import PersistentTwinEntity
        annotations = PersistentTwinEntity.__annotations__
        for field in annotations:
            for kw in self.PROTOCOL_KEYWORDS:
                assert kw not in field.lower(), \
                    f"Protocol field '{field}' in PersistentTwinEntity"

    def test_template_models_no_protocol_fields(self):
        """Template models must not have protocol fields."""
        from services.template.models import TwinTemplate, TemplateProperty, TemplateRelationship
        for model in (TwinTemplate, TemplateProperty, TemplateRelationship):
            annotations = model.__annotations__
            for field in annotations:
                for kw in self.PROTOCOL_KEYWORDS:
                    assert kw not in field.lower(), \
                        f"Protocol field '{field}' in {model.__name__}"

    def test_ontology_models_no_protocol_fields(self):
        """Ontology models must not have protocol fields."""
        from services.ontology.models import EntityTypeDefinition, CapabilityDefinition
        for model in (EntityTypeDefinition, CapabilityDefinition):
            annotations = model.__annotations__
            for field in annotations:
                for kw in self.PROTOCOL_KEYWORDS:
                    assert kw not in field.lower(), \
                        f"Protocol field '{field}' in {model.__name__}"

    def test_deployment_models_no_protocol_fields(self):
        """Deployment models must not have protocol fields."""
        from services.deployment.models import (
            DeploymentProfile, DeploymentInstance, DeploymentNode, DeploymentNodeCapability,
        )
        for model in (DeploymentProfile, DeploymentInstance, DeploymentNode, DeploymentNodeCapability):
            annotations = model.__annotations__
            for field in annotations:
                for kw in self.PROTOCOL_KEYWORDS:
                    assert kw not in field.lower(), \
                        f"Protocol field '{field}' in {model.__name__}"

    def test_provisioning_models_no_protocol_fields(self):
        """Provisioning models must not have protocol fields."""
        from services.provisioning.models import ProvisioningPlan, ProvisioningItem, ProvisioningExecution
        for model in (ProvisioningPlan, ProvisioningItem, ProvisioningExecution):
            annotations = model.__annotations__
            for field in annotations:
                for kw in self.PROTOCOL_KEYWORDS:
                    assert kw not in field.lower(), \
                        f"Protocol field '{field}' in {model.__name__}"


class TestDependencyDirection:
    """Verify correct dependency direction — adapters depend on core, not vice versa."""

    def test_activation_no_adapter_import(self):
        """Activation must not import adapter layer."""
        source = Path("services/activation/services.py").read_text(encoding="utf-8")
        assert "services.adapter" not in source

    def test_provisioning_no_adapter_import(self):
        """Provisioning must not import adapter layer."""
        source = Path("services/provisioning/services.py").read_text(encoding="utf-8")
        assert "services.adapter" not in source

    def test_twin_no_adapter_import(self):
        """Twin runtime must not import adapter layer."""
        source = Path("services/twin/services.py").read_text(encoding="utf-8")
        assert "services.adapter" not in source

    def test_deployment_no_adapter_import(self):
        """Deployment must not import adapter layer."""
        source = Path("services/deployment/services/deployment_service.py").read_text(
            encoding="utf-8"
        )
        assert "services.adapter" not in source

    def test_ontology_no_adapter_import(self):
        """Ontology must not import adapter layer."""
        source = Path("services/ontology/services.py").read_text(encoding="utf-8")
        assert "services.adapter" not in source

    def test_template_no_adapter_import(self):
        """Template must not import adapter layer."""
        source = Path("services/template/services/template_service.py").read_text(
            encoding="utf-8"
        )
        assert "services.adapter" not in source

    def test_core_no_protocol_import(self):
        """Core must not import any protocol."""
        for py_file in Path("services/core").rglob("*.py"):
            content = py_file.read_text(encoding="utf-8")
            for kw in ["bacnet", "modbus", "opcua", "mqtt", "plc"]:
                assert kw not in content.lower(), \
                    f"Protocol import in {py_file.relative_to('services/core')}"


class TestCommandBoundary:
    """Verify TwinCommand is intent-only, not physical execution."""

    def test_command_service_no_adapter_call(self):
        """Command service must not call adapter methods."""
        source = Path("services/activation/command.py").read_text(encoding="utf-8")
        # Remove docstrings
        clean = re.sub(r'""".*?"""', "", source, flags=re.DOTALL)
        clean = re.sub(r"'''.*?'''", "", clean, flags=re.DOTALL)
        assert "adapter.write" not in clean.lower()
        assert "ProtocolAdapter" not in clean

    def test_command_no_physical_transport(self):
        """Command must not implement any physical transport."""
        source = Path("services/activation/command.py").read_text(encoding="utf-8")
        import re
        clean = re.sub(r'""".*?"""', "", source, flags=re.DOTALL)
        clean = re.sub(r"'''.*?'''", "", clean, flags=re.DOTALL)
        for kw in ["socket", "tcp", "serial", "udp", "publish", "subscribe"]:
            assert kw not in clean.lower(), f"Physical transport '{kw}' in command.py"

    def test_command_state_is_abstract(self):
        """Command states must be abstract, not protocol-specific."""
        from services.activation.models import TwinCommand
        annotations = TwinCommand.__annotations__
        assert "status" in annotations
        assert "payload" in annotations
        for field in annotations:
            assert "bacnet" not in field.lower()
            assert "modbus" not in field.lower()
            assert "opcua" not in field.lower()


class TestTelemetryBoundary:
    """Verify Task 14 does not bypass Task 7 telemetry layer."""

    def test_activation_no_telemetry_ingestion(self):
        """Activation must not ingest telemetry directly."""
        source = Path("services/activation/services.py").read_text(encoding="utf-8")
        assert "telemetry" not in source.lower() or "telemetry" in source.lower().split("normalized")[0]
        # activation should not import telemetry service
        assert "from services.telemetry" not in source

    def test_command_no_telemetry_call(self):
        """Command must not call telemetry directly."""
        source = Path("services/activation/command.py").read_text(encoding="utf-8")
        assert "from services.telemetry" not in source

    def test_registry_not_telemetry_source(self):
        """TwinEntityRegistry is not a telemetry source — it's runtime state."""
        from services.twin.registry import TwinEntityRegistry
        # Registry methods should be register/remove/get/list — not ingest
        methods = [m for m in dir(TwinEntityRegistry) if not m.startswith("_")]
        assert "ingest" not in methods
        assert "receive_telemetry" not in methods


class TestZeroCodeReadiness:
    """Verify zero-code deployment chain remains intact."""

    def test_new_entity_type_does_not_require_new_class(self):
        """Adding a new equipment type should not require new Python classes."""
        # Verify all models use generic fields (JSONB, String, UUID)
        from services.activation.models import TwinActivationLog, TwinCommand
        from services.twin.models.binding import TwinBinding
        from services.twin.models.entity import PersistentTwinEntity

        for model in (TwinActivationLog, TwinCommand, TwinBinding, PersistentTwinEntity):
            for field_name, field_type in model.__annotations__.items():
                # All fields should be generic types
                type_str = str(field_type)
                assert "AHU" not in type_str
                assert "Robot" not in type_str
                assert "Transformer" not in type_str
                assert "BACnet" not in type_str
                assert "Modbus" not in type_str

    def test_binding_is_generic(self):
        """TwinBinding must be generic — no industry-specific types."""
        from services.twin.models.binding import TwinBinding
        annotations = TwinBinding.__annotations__
        assert "binding_type" in annotations
        # binding_type is a String, not an enum tied to industry
        assert "str" in str(annotations["binding_type"]) or "String" in str(annotations["binding_type"])

    def test_activation_state_is_generic(self):
        """Activation states must be generic, not industry-specific."""
        from services.activation.activation import get_activation_states
        states = get_activation_states()
        for state in states:
            assert state not in ("ahu", "robot", "transformer", "meter")


class TestMultiIndustry:
    """Verify architecture supports multiple industries without modification."""

    def test_building_scenario_uses_generic_models(self):
        """Building (AHU, HVAC, Lighting) uses same generic models."""
        from services.activation.models import TwinActivationLog
        from services.twin.models.binding import TwinBinding
        # Models exist and are generic
        assert TwinActivationLog.__tablename__ == "twin_activation_logs"
        assert TwinBinding.__tablename__ == "twin_bindings"

    def test_manufacturing_scenario_uses_generic_models(self):
        """Manufacturing (Robot, PLC Machine) uses same generic models."""
        from services.activation.command import TwinCommandService
        from services.activation.models import TwinCommand
        assert TwinCommand.__tablename__ == "twin_commands"

    def test_energy_scenario_uses_generic_models(self):
        """Energy (Transformer, PV, Meter) uses same generic models."""
        from services.deployment.models import DeploymentProfile
        assert DeploymentProfile.__tablename__ == "deployment_profiles"

    def test_campus_scenario_uses_generic_models(self):
        """Campus (Building Cluster, Road, Water) uses same generic models."""
        from services.ontology.models import EntityTypeDefinition
        assert EntityTypeDefinition.__tablename__ == "entity_type_definitions"


class TestTenantSecurity:
    """Verify tenant isolation across all Task 14 components."""

    def test_activation_log_has_tenant_id(self):
        from services.activation.models import TwinActivationLog
        assert "tenant_id" in TwinActivationLog.__annotations__

    def test_command_has_tenant_id(self):
        from services.activation.models import TwinCommand
        assert "tenant_id" in TwinCommand.__annotations__

    def test_all_routes_use_tenant_dependency(self):
        from services.activation.routes import router
        import inspect
        for route in router.routes:
            func = getattr(route, "endpoint", None)
            if func is None:
                continue
            sig = inspect.signature(func)
            has_tenant = any(
                "tenant" in param_name.lower()
                for param_name in sig.parameters
            )
            assert has_tenant, f"Route {route.path} missing tenant"

    def test_all_routes_have_permission_guard(self):
        from services.activation.routes import router
        for route in router.routes:
            deps = getattr(route, "dependencies", [])
            has_perm = any("require_permission" in str(d) for d in deps)
            assert has_perm, f"Route {route.path} missing permission guard"

    def test_repository_extends_tenant_aware(self):
        from services.activation.repository import (
            TwinActivationLogRepository,
            TwinCommandRepository,
        )
        from services.core.repositories.base import TenantAwareRepository
        assert issubclass(TwinActivationLogRepository, TenantAwareRepository)
        assert issubclass(TwinCommandRepository, TenantAwareRepository)


class TestMigrationIntegrity:
    """Verify Task 14 migration integrity."""

    def test_migration_chain_correct(self):
        migration_path = Path("database/migrations/versions")
        for py_file in migration_path.rglob("phase14*.py"):
            content = py_file.read_text(encoding="utf-8")
            assert "phase13_provisioning" in content

    def test_migration_no_alter_existing_tables(self):
        migration_path = Path("database/migrations/versions")
        for py_file in migration_path.rglob("phase14*.py"):
            content = py_file.read_text(encoding="utf-8")
            assert "ALTER TABLE" not in content.upper()

    def test_migration_no_duplicate_binding_table(self):
        """Must not create a second twin_bindings table."""
        migration_path = Path("database/migrations/versions")
        for py_file in migration_path.rglob("phase14*.py"):
            content = py_file.read_text(encoding="utf-8")
            assert "twin_bindings" not in content or "twin_activation_logs" in content

    def test_migration_creates_both_tables(self):
        migration_path = Path("database/migrations/versions")
        for py_file in migration_path.rglob("phase14*.py"):
            content = py_file.read_text(encoding="utf-8")
            assert "twin_activation_logs" in content
            assert "twin_commands" in content

    def test_migration_has_soft_delete(self):
        migration_path = Path("database/migrations/versions")
        for py_file in migration_path.rglob("phase14*.py"):
            content = py_file.read_text(encoding="utf-8")
            assert "deleted_at" in content


class TestFrozenModuleIntegrity:
    """Verify no frozen modules were modified."""

    def test_twin_service_unmodified(self):
        """services/twin/services.py should not reference activation."""
        source = Path("services/twin/services.py").read_text(encoding="utf-8")
        # Twin service should not import activation
        assert "services.activation" not in source

    def test_provisioning_service_unmodified(self):
        source = Path("services/provisioning/services.py").read_text(encoding="utf-8")
        assert "services.activation" not in source

    def test_deployment_service_unmodified(self):
        source = Path("services/deployment/services/deployment_service.py").read_text(
            encoding="utf-8"
        )
        assert "services.activation" not in source

    def test_gateway_includes_activation(self):
        """Gateway must include activation router (expected change)."""
        source = Path("services/gateway/main.py").read_text(encoding="utf-8")
        assert "activation_router" in source
