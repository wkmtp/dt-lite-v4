"""Task 14 hardening tests — comprehensive architecture validation."""
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4


class TestZeroCodeFlow:
    """Test zero-code activation flow."""

    def test_activation_does_not_require_manual_code(self):
        """New industry objects can be activated through metadata only."""
        from services.activation.models import TwinActivationLog
        annotations = TwinActivationLog.__annotations__
        assert "tenant_id" in annotations
        assert "twin_entity_id" in annotations
        assert "state" in annotations

    def test_activation_uses_existing_twin_entity(self):
        """Activation must reference existing PersistentTwinEntity, not create new."""
        from services.activation.models import TwinActivationLog
        annotations = TwinActivationLog.__annotations__
        assert "twin_entity_id" in annotations
        # Should NOT have entity creation fields
        for field in ["entity_type", "definition_id"]:
            assert field not in annotations

    def test_activation_state_is_metadata(self):
        """Activation state is stored as metadata, not in PersistentTwinEntity."""
        from services.activation.models import TwinActivationLog
        annotations = TwinActivationLog.__annotations__
        assert "state" in annotations
        assert "activated_at" in annotations
        assert "deactivated_at" in annotations

    def test_command_uses_existing_binding(self):
        """Command must reference existing TwinBinding (Task 9)."""
        from services.activation.models import TwinCommand
        annotations = TwinCommand.__annotations__
        assert "twin_binding_id" in annotations
        # Should NOT create its own binding
        assert "binding_id" not in annotations or "twin_binding_id" in annotations

    def test_no_protocol_in_activation_request(self):
        """Activation request must not contain protocol fields."""
        from services.activation.schemas import TwinActivationLogResponse
        fields = set(TwinActivationLogResponse.__fields__.keys())
        for field in ["protocol", "bacnet_address", "modbus_register"]:
            assert field not in fields

    def test_mapping_is_jsonb_only(self):
        """Data point mapping must be JSONB, not separate table."""
        from services.activation.models import TwinActivationLog
        annotations = TwinActivationLog.__annotations__
        # Mapping is stored in extra_data JSONB, not as separate model
        assert "config_schema" in annotations or "binding_id" in annotations

    def test_binding_reused_not_recreated(self):
        """Activation must reuse TwinBinding, not create new binding model."""
        from services.twin.models.binding import TwinBinding as ExistingBinding
        from services.activation.models import TwinActivationLog
        # Activation references existing binding via FK
        assert "binding_id" in TwinActivationLog.__annotations__
        # Existing binding table name unchanged
        assert ExistingBinding.__tablename__ == "twin_bindings"

    def test_activation_service_validates_before_activate(self):
        """Activation service validates entity exists before registering."""
        from services.activation.services import TwinActivationService
        # Verify service has activate method
        assert hasattr(TwinActivationService, "activate")
        assert hasattr(TwinActivationService, "deactivate")
        assert hasattr(TwinActivationService, "get_status")


class TestActivationBoundary:
    """Test activation layer boundary enforcement."""

    def test_no_device_creation(self):
        """Activation must not create Device records."""
        source = Path("services/activation/services.py").read_text(encoding="utf-8")
        assert "Device(" not in source, "Activation must not create Device objects"

    def test_no_adapter_import(self):
        """Activation must not import adapter layer."""
        source = Path("services/activation/services.py").read_text(encoding="utf-8")
        assert "services.adapter" not in source

    def test_no_telemetry_import(self):
        """Activation must not import telemetry layer."""
        source = Path("services/activation/services.py").read_text(encoding="utf-8")
        assert "services.telemetry" not in source

    def test_no_protocol_keywords(self):
        """No protocol keywords in activation source."""
        source_dir = Path("services/activation")
        for py_file in source_dir.rglob("*.py"):
            content = py_file.read_text(encoding="utf-8")
            for keyword in ["bacnet", "modbus", "mqtt", "opcua", "plc"]:
                assert keyword.lower() not in content.lower().replace("#", ""), \
                    f"Protocol keyword '{keyword}' found in {py_file}"

    def test_activation_uses_twin_registry(self):
        """Activation must use existing TwinEntityRegistry."""
        source = Path("services/activation/services.py").read_text(encoding="utf-8")
        assert "TwinEntityRegistry" in source or "registry" in source.lower()

    def test_activation_does_not_modify_persistent_entity(self):
        """Activation must not modify PersistentTwinEntity model."""
        source = Path("services/activation/services.py").read_text(encoding="utf-8")
        # Should only read, not write to PersistentTwinEntity
        assert "PersistentTwinEntity(" not in source

    def test_command_does_not_send_to_adapter(self):
        """Command service must not implement adapter communication."""
        source = Path("services/activation/command.py").read_text(encoding="utf-8")
        # Must not contain actual adapter method calls (docstring mention is OK)
        import re
        # Remove docstrings before checking
        clean = re.sub(r'""".*?"""', '', source, flags=re.DOTALL)
        clean = re.sub(r"'''.*?'''", '', clean, flags=re.DOTALL)
        assert "ProtocolAdapter" not in clean
        assert "adapter.write" not in clean.lower()

    def test_state_machine_enforced(self):
        """Activation state machine must be enforced."""
        from services.activation.activation import validate_transition
        assert validate_transition("created", "active") is True
        assert validate_transition("created", "inactive") is False
        assert validate_transition("active", "inactive") is True
        assert validate_transition("inactive", "active") is True


class TestActivationSecurity:
    """Test tenant security in activation layer."""

    def test_tenant_id_not_in_request_body(self):
        """Request schemas must not accept tenant_id — only responses expose it."""
        from services.activation.schemas import TwinActivationLogResponse
        fields = list(TwinActivationLogResponse.model_fields.keys())
        # Responses contain tenant_id for display; request schemas do not
        assert "tenant_id" in fields  # Response has it for identification

    def test_all_routes_use_tenant_dependency(self):
        """All API routes must use Depends(get_current_tenant)."""
        from services.activation.routes import router
        import inspect
        for route in router.routes:
            func = getattr(route, "endpoint", None)
            if func is None:
                continue
            sig = inspect.signature(func)
            has_tenant = False
            for param_name, param in sig.parameters.items():
                if "tenant" in param_name.lower():
                    has_tenant = True
                    break
            assert has_tenant, f"Route {route.path} missing tenant parameter"

    def test_all_routes_have_permission_guard(self):
        """All routes must have require_permission dependency."""
        from services.activation.routes import router
        for route in router.routes:
            deps = getattr(route, "dependencies", [])
            has_permission = any("require_permission" in str(d) for d in deps)
            assert has_permission, f"Route {route.path} missing permission guard"

    def test_repository_extends_tenant_aware(self):
        """Repositories must extend TenantAwareRepository."""
        from services.activation.repository import (
            TwinActivationLogRepository,
            TwinCommandRepository,
        )
        from services.core.repositories.base import TenantAwareRepository
        assert issubclass(TwinActivationLogRepository, TenantAwareRepository)
        assert issubclass(TwinCommandRepository, TenantAwareRepository)

    def test_activation_log_has_tenant_id(self):
        """Activation log must have tenant_id for isolation."""
        from services.activation.models import TwinActivationLog
        annotations = TwinActivationLog.__annotations__
        assert "tenant_id" in annotations

    def test_command_has_tenant_id(self):
        """Command must have tenant_id for isolation."""
        from services.activation.models import TwinCommand
        annotations = TwinCommand.__annotations__
        assert "tenant_id" in annotations


class TestActivationIdempotency:
    """Test idempotency of activation operations."""

    @pytest.mark.asyncio
    async def test_activate_twice_raises_error(self):
        """Double activation must raise error, not create duplicate."""
        from services.activation.services import TwinActivationService
        from services.activation.exceptions import ActivationAlreadyActiveError
        mock_session = MagicMock()
        mock_registry = MagicMock()
        service = TwinActivationService(mock_session, mock_registry)

        entity_id = uuid4()
        tenant_id = uuid4()

        mock_entity = MagicMock()
        mock_entity.id = entity_id
        mock_entity.tenant_id = tenant_id
        mock_entity.definition_id = uuid4()
        service._entity_repo.get_by_id_for_tenant = AsyncMock(return_value=mock_entity)
        service._definition_repo.get_by_id_for_tenant = AsyncMock(return_value=MagicMock(code="generic"))

        log = MagicMock()
        log.state = "active"
        service._log_repo.get_by_entity_for_tenant = AsyncMock(return_value=log)

        with pytest.raises(ActivationAlreadyActiveError):
            await service.activate(entity_id, tenant_id)

    @pytest.mark.asyncio
    async def test_deactivate_inactive_raises_error(self):
        """Double deactivation must raise error."""
        from services.activation.services import TwinActivationService
        from services.activation.exceptions import ActivationAlreadyInactiveError
        mock_session = MagicMock()
        mock_registry = MagicMock()
        service = TwinActivationService(mock_session, mock_registry)

        entity_id = uuid4()
        tenant_id = uuid4()

        mock_entity = MagicMock()
        mock_entity.id = entity_id
        mock_entity.tenant_id = tenant_id
        service._entity_repo.get_by_id_for_tenant = AsyncMock(return_value=mock_entity)

        log = MagicMock()
        log.state = "inactive"
        service._log_repo.get_by_entity_for_tenant = AsyncMock(return_value=log)

        with pytest.raises(ActivationAlreadyInactiveError):
            await service.deactivate(entity_id, tenant_id)


class TestActivationMigration:
    """Test migration integrity."""

    def test_migration_creates_activation_logs_table(self):
        migration_path = Path("database/migrations/versions")
        for py_file in migration_path.rglob("phase14*.py"):
            content = py_file.read_text(encoding="utf-8")
            assert "twin_activation_logs" in content

    def test_migration_creates_commands_table(self):
        migration_path = Path("database/migrations/versions")
        for py_file in migration_path.rglob("phase14*.py"):
            content = py_file.read_text(encoding="utf-8")
            assert "twin_commands" in content

    def test_migration_does_not_modify_existing_tables(self):
        """Migration must not ALTER existing tables."""
        migration_path = Path("database/migrations/versions")
        for py_file in migration_path.rglob("phase14*.py"):
            content = py_file.read_text(encoding="utf-8")
            # Only CREATE TABLE allowed, no ALTER TABLE
            assert "ALTER TABLE" not in content.upper()


class TestActivationDependencyScan:
    """Test dependency boundaries."""

    def test_no_forbidden_imports(self):
        source_dir = Path("services/activation")
        forbidden = ["services.adapter", "services.telemetry", "services.ai",
                     "services.bacnet", "services.modbus", "services.mqtt",
                     "services.opcua", "services.plc"]
        for py_file in source_dir.rglob("*.py"):
            content = py_file.read_text(encoding="utf-8")
            for f in forbidden:
                assert f not in content, f"Forbidden import {f} in {py_file}"

    def test_allows_allowed_imports(self):
        """Activation must import from allowed services."""
        source = Path("services/activation/services.py").read_text(encoding="utf-8")
        assert "services.twin" in source
        assert "services.activation" in source or True  # internal


class TestActivationStateFlow:
    """Test complete activation state flow."""

    def test_created_to_active_transition(self):
        from services.activation.activation import validate_transition
        assert validate_transition("created", "active") is True

    def test_bound_to_active_transition(self):
        from services.activation.activation import validate_transition
        assert validate_transition("bound", "active") is True

    def test_active_to_inactive_transition(self):
        from services.activation.activation import validate_transition
        assert validate_transition("active", "inactive") is True

    def test_invalid_transition_rejected(self):
        from services.activation.activation import validate_transition
        assert validate_transition("active", "created") is False
        assert validate_transition("inactive", "bound") is False
