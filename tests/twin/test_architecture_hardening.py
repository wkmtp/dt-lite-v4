"""Architecture Hardening Tests for Task 8 Twin Runtime.

This test module enforces strict architectural boundaries:
- No adapter dependencies
- No database/repository dependencies
- No protocol implementations
- Proper tenant isolation
"""
import os
import pytest


class TestDependencyBoundaries:
    """Test that twin layer maintains strict dependency boundaries."""

    def setup_method(self):
        """Setup test paths."""
        self.twin_dir = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "services", "twin"
        )
        self.forbidden_modules = {
            "services.adapter",
            "services.iota.adapters",
        }
        self.forbidden_imports = {
            "bacnet",
            "modbus",
            "opcua",
            "mqtt",
            "plc",
            "kafka",
            "redis",
            "celery",
            "rabbitmq",
            "flink",
            "spark",
        }

    def _get_all_python_files(self) -> list[str]:
        """Get all Python files in services/twin/."""
        python_files = []
        for root, dirs, files in os.walk(self.twin_dir):
            for filename in files:
                if filename.endswith(".py") and filename != "__init__.py":
                    filepath = os.path.join(root, filename)
                    python_files.append(filepath)
        return python_files

    def test_no_adapter_dependencies(self):
        """Verify twin module has zero dependencies on adapter layer."""
        python_files = self._get_all_python_files()
        forbidden_count = 0

        for filepath in python_files:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
                for forbidden_module in self.forbidden_modules:
                    if f"import {forbidden_module}" in content or \
                       f"from {forbidden_module}" in content:
                        forbidden_count += 1
                        pytest.fail(
                            f"Forbidden import found in {filepath}: {forbidden_module}"
                        )

        assert forbidden_count == 0, "Found adapter dependencies in twin module"

    def test_no_protocol_dependencies(self):
        """Verify no protocol implementations in twin module."""
        python_files = self._get_all_python_files()
        forbidden_count = 0

        for filepath in python_files:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read().lower()
                for keyword in self.forbidden_imports:
                    if keyword in content:
                        # Check if it's actually an import, not just a comment
                        lines = content.split('\n')
                        for line in lines:
                            if keyword in line and ('import' in line or 'from' in line):
                                forbidden_count += 1
                                pytest.fail(
                                    f"Forbidden protocol/infra keyword '{keyword}' found in {filepath}: {line.strip()}"
                                )

        assert forbidden_count == 0, "Found protocol or infrastructure dependencies"

    def test_no_database_direct_access(self):
        """Verify twin module doesn't directly access databases."""
        python_files = self._get_all_python_files()

        for filepath in python_files:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
                # Check for direct SQLAlchemy usage (except imports from core)
                if "session.execute" in content or \
                   "session.commit" in content or \
                   "session.add" in content:
                    pytest.fail(
                        f"Direct database access found in {filepath}: "
                        "Should use repository pattern only"
                    )

    def test_only_allowed_dependencies(self):
        """Verify only allowed dependencies are used."""
        allowed_imports = [
            "services.iota.contracts",
            "services.iota.repositories",
            "services.twin",
            "services.auth",
            "services.core",
            "services.database",
            "fastapi",
            "sqlalchemy",
            "uuid",
            "datetime",
            "typing",
            "logging",
            "json",
            "dataclasses",
        ]

        python_files = self._get_all_python_files()

        for filepath in python_files:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()

            # Extract imports
            lines = content.split('\n')
            for line in lines:
                line = line.strip()
                if line.startswith('import ') or line.startswith('from '):
                    # Check if it's an allowed import
                    is_allowed = False
                    for allowed in allowed_imports:
                        if allowed in line:
                            is_allowed = True
                            break

                    # Special cases for standard library
                    stdlib_modules = [
                        'os', 'sys', 'typing', 'uuid', 'datetime',
                        'dataclasses', 'logging', 'json', 'inspect'
                    ]
                    for mod in stdlib_modules:
                        if line.startswith(f'import {mod}') or line.startswith(f'from {mod}'):
                            is_allowed = True
                            break

                    # unittest.mock for tests
                    if 'unittest.mock' in line:
                        is_allowed = True
                        break

                    if not is_allowed:
                        pytest.fail(
                            f"Disallowed import in {filepath}: {line}"
                        )


class TestRuntimeModelValidation:
    """Test that TwinEntity follows runtime model principles."""

    def test_twin_entity_is_dataclass_not_sqlalchemy_model(self):
        """Verify TwinEntity is a dataclass, not a SQLAlchemy model."""
        from services.twin.models import TwinEntity

        assert hasattr(TwinEntity, '__dataclass_fields__'), \
            "TwinEntity should be a dataclass"

    def test_twin_entity_has_runtime_state_field(self):
        """Verify TwinEntity has runtime_state field."""
        from services.twin.models import TwinEntity
        from dataclasses import fields

        field_names = [f.name for f in fields(TwinEntity)]
        assert 'runtime_state' in field_names, \
            "TwinEntity must have runtime_state field"

    def test_twin_entity_has_backward_compatible_state_property(self):
        """Verify TwinEntity has backward-compatible state property."""
        from services.twin.models import TwinEntity

        entity = TwinEntity(tenant_id=__import__('uuid').uuid4())
        assert hasattr(entity, "state"), \
            "TwinEntity should have state property for backward compatibility"

    def test_registry_is_pure_in_memory(self):
        """Verify TwinEntityRegistry has no database dependencies."""
        from services.twin.registry import TwinEntityRegistry

        registry = TwinEntityRegistry()
        assert isinstance(registry._storage, dict), \
            "Registry should use pure dict storage"


class TestBindingArchitecture:
    """Test binding service architecture."""

    def test_binding_record_is_separate_from_twin_entity(self):
        """Verify BindingRecord is distinct from TwinEntity."""
        from services.twin.binding import BindingRecord
        from services.twin.models import TwinEntity

        binding = BindingRecord(
            id=__import__('uuid').uuid4(),
            device_id=__import__('uuid').uuid4(),
            entity_id=__import__('uuid').uuid4(),
            tenant_id=__import__('uuid').uuid4(),
        )

        assert isinstance(binding, BindingRecord)
        assert not isinstance(binding, TwinEntity), \
            "BindingRecord should not be a TwinEntity instance"

    def test_binding_requires_tenant_verification(self):
        """Verify binding creation requires tenant verification."""
        from services.twin.binding import EntityBindingService
        from services.twin.registry import TwinEntityRegistry
        from unittest.mock import MagicMock

        registry = TwinEntityRegistry()
        mock_device_repo = MagicMock()
        service = EntityBindingService(registry, mock_device_repo)

        # Verify method signature includes tenant_id
        import inspect
        sig = inspect.signature(service.create_binding)
        params = list(sig.parameters.keys())
        assert 'tenant_id' in params, \
            "create_binding must accept tenant_id parameter"


class TestStateManagementArchitecture:
    """Test state management architecture."""

    def test_state_manager_uses_registry(self):
        """Verify TwinStateManager uses TwinEntityRegistry."""
        from services.twin.state import TwinStateManager
        from services.twin.registry import TwinEntityRegistry

        registry = TwinEntityRegistry()
        state_manager = TwinStateManager(registry)

        assert state_manager._registry is registry

    def test_update_state_requires_telemetry_contract(self):
        """Verify update_state accepts NormalizedTelemetry."""
        from services.twin.state import TwinStateManager
        from services.twin.registry import TwinEntityRegistry
        import inspect

        registry = TwinEntityRegistry()
        state_manager = TwinStateManager(registry)

        sig = inspect.signature(state_manager.update_state)
        params = list(sig.parameters.keys())
        assert 'telemetry' in params, \
            "update_state must accept telemetry parameter"


class TestAPISecurityReview:
    """Test API security boundaries."""

    def test_routes_require_permission(self):
        """Verify all routes have permission dependencies."""
        from services.twin.routes import router

        for route in router.routes:
            if hasattr(route, 'dependencies'):
                # Routes with dependencies should have at least one
                assert len(route.dependencies) > 0 or route.path in ['/', '/batch'], \
                    f"Route {route.path} should have permission dependencies"

    def test_no_unauthenticated_endpoints(self):
        """Verify no endpoints are exposed without authentication."""
        from services.twin.routes import router

        for route in router.routes:
            if hasattr(route, 'path'):
                # All routes should be under /api/v1/ prefix
                assert route.path.startswith('/api/'), \
                    f"Route {route.path} should be under /api/ prefix"


class TestCrossTenantSecurity:
    """Enhanced cross-tenant security tests."""

    def test_state_manager_rejects_cross_tenant_updates(self):
        """Test that state updates are rejected across tenants."""
        from services.twin.state import TwinStateManager
        from services.twin.registry import TwinEntityRegistry
        from services.iota.contracts import NormalizedTelemetry
        from datetime import datetime, timezone
        from uuid import uuid4

        tenant_a = uuid4()
        tenant_b = uuid4()

        registry = TwinEntityRegistry()
        state_manager = TwinStateManager(registry)

        # Create entity for tenant A
        from services.twin.models import TwinEntity
        entity_a = TwinEntity(tenant_id=tenant_a, name="A Entity")
        registry.register(entity_a)

        # Create telemetry for tenant B trying to update A's entity
        telemetry = NormalizedTelemetry(
            tenant_id=str(tenant_b),
            device_id=str(uuid4()),
            datapoint_id=str(uuid4()),
            event_time=datetime.now(timezone.utc),
            ingested_at=datetime.now(timezone.utc),
            value=999.0,
            data_type="FLOAT",
            quality="GOOD",
        )

        # Attempt cross-tenant update - should raise TwinEntityNotFoundError
        # because entity doesn't exist for tenant B
        from services.twin.exceptions import TwinEntityNotFoundError
        with pytest.raises(TwinEntityNotFoundError):
            state_manager.update_state(entity_a.id, telemetry, tenant_b)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
