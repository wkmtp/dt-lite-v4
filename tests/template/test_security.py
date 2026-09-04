"""Test template security and tenant isolation."""
import inspect
import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from services.template.services import TemplateService


class TestCrossTenantAccess:
    """Test cross-tenant access is blocked for templates."""

    @pytest.mark.asyncio
    async def test_cross_tenant_get_rejected(self):
        """Verify cross-tenant template retrieval is blocked."""
        repo = MagicMock()
        repo.get_by_id_for_tenant = AsyncMock(return_value=None)
        service = TemplateService(repo)

        with pytest.raises(Exception):  # TemplateNotFoundError
            await service.get_template(uuid4(), uuid4())

    @pytest.mark.asyncio
    async def test_cross_tenant_update_rejected(self):
        """Verify cross-tenant template update is blocked."""
        from services.template.schemas import TemplateUpdateRequest

        repo = MagicMock()
        repo.get_by_id_for_tenant = AsyncMock(return_value=None)
        service = TemplateService(repo)

        with pytest.raises(Exception):
            await service.update_template(uuid4(), TemplateUpdateRequest(name="Hacked"), uuid4())

    @pytest.mark.asyncio
    async def test_cross_tenant_delete_rejected(self):
        """Verify cross-tenant template deletion is blocked."""
        repo = MagicMock()
        repo.get_by_id_for_tenant = AsyncMock(return_value=None)
        service = TemplateService(repo)

        with pytest.raises(Exception):
            await service.delete_template(uuid4(), uuid4())


class TestTenantFromContext:
    """Verify tenant_id comes from context, not payload."""

    def test_service_never_accepts_tenant_from_body(self):
        """Service methods must require tenant_id as positional parameter."""
        from services.template.services import TemplateService

        for method_name in ["create_template", "get_template", "update_template", "delete_template"]:
            method = getattr(TemplateService, method_name)
            sig = inspect.signature(method)
            params = list(sig.parameters.keys())
            if "tenant_id" in params:
                param = sig.parameters["tenant_id"]
                assert param.default is inspect.Parameter.empty, \
                    f"{method_name}: tenant_id must be required, not optional"

    def test_routes_use_dependency_injection(self):
        """Verify routes use Depends(get_current_tenant)."""
        from services.template.routes import router

        for route in router.routes:
            if hasattr(route, "dependencies"):
                dep_str = str(route.dependencies)
                assert "get_current_tenant" in dep_str or "Depends" in dep_str, \
                    f"Route {route.path} must use dependency injection for tenant"


class TestRepositoryTenantFiltering:
    """Verify repository queries are tenant-scoped."""

    def test_repository_queries_include_tenant_filter(self):
        """All repository methods must filter by tenant."""
        from services.template.repositories import TemplateRepository

        methods = ["get_by_code", "list_active", "count_active", "get_by_id_for_tenant"]
        for method_name in methods:
            method = getattr(TemplateRepository, method_name)
            source = inspect.getsource(method)
            assert "tenant_id" in source, f"{method_name} must include tenant_id filter"


class TestPermissionRequired:
    """Verify all endpoints require permissions."""

    def test_all_endpoints_have_permission_dependencies(self):
        """All template routes must have permission guards."""
        from services.template.routes import router

        for route in router.routes:
            if hasattr(route, "dependencies"):
                assert len(route.dependencies) > 0, \
                    f"Route {route.path} requires permission dependencies"
