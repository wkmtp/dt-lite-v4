"""Test ontology security and tenant isolation."""
import inspect
import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from services.ontology.services import OntologyService


class TestCrossTenantAccess:
    """Test cross-tenant access is blocked for ontology entities."""

    @pytest.mark.asyncio
    async def test_cross_tenant_concept_get_rejected(self):
        """Verify cross-tenant concept retrieval is blocked."""
        repo = MagicMock()
        repo.get_by_id_for_tenant = AsyncMock(return_value=None)
        service = OntologyService(repo)

        with pytest.raises(Exception):
            await service.get_concept(uuid4(), uuid4())

    @pytest.mark.asyncio
    async def test_cross_tenant_concept_update_rejected(self):
        """Verify cross-tenant concept update is blocked."""
        from services.ontology.schemas import ConceptUpdateRequest

        repo = MagicMock()
        repo.get_by_id_for_tenant = AsyncMock(return_value=None)
        service = OntologyService(repo)

        with pytest.raises(Exception):
            await service.update_concept(uuid4(), ConceptUpdateRequest(name="Hacked"), uuid4())


class TestTenantFromContext:
    """Verify tenant_id comes from context, not payload."""

    def test_service_never_accepts_tenant_from_body(self):
        """Service methods must require tenant_id as positional parameter."""
        for method_name in ["create_concept", "get_concept", "update_concept"]:
            method = getattr(OntologyService, method_name)
            sig = inspect.signature(method)
            params = list(sig.parameters.keys())
            if "tenant_id" in params:
                param = sig.parameters["tenant_id"]
                assert param.default is inspect.Parameter.empty, \
                    f"{method_name}: tenant_id must be required, not optional"

    def test_routes_use_dependency_injection(self):
        """Verify routes use Depends(get_current_tenant)."""
        from services.ontology.routes import router

        for route in router.routes:
            if hasattr(route, "endpoint"):
                src = inspect.getsource(route.endpoint)
                dep_str = str(route.dependencies)
                has_dep_in_params = "get_current_tenant" in src
                has_dep_in_list = "get_current_tenant" in dep_str
                assert has_dep_in_params or has_dep_in_list, \
                    f"Route {route.path} must use get_current_tenant"


class TestRepositoryTenantFiltering:
    """Verify repository queries are tenant-scoped."""

    def test_repository_queries_include_tenant_filter(self):
        """All repository methods must filter by tenant."""
        from services.ontology.repository import OntologyRepository

        methods = ["get_by_code", "count_active", "get_by_id_for_tenant"]
        for method_name in methods:
            method = getattr(OntologyRepository, method_name)
            source = inspect.getsource(method)
            assert "tenant_id" in source, f"{method_name} must include tenant_id filter"


class TestPermissionRequired:
    """Verify all endpoints require permissions."""

    def test_all_endpoints_have_permission_dependencies(self):
        """All ontology routes must have permission guards."""
        from services.ontology.routes import router

        for route in router.routes:
            if hasattr(route, "dependencies"):
                assert len(route.dependencies) > 0, \
                    f"Route {route.path} requires permission dependencies"
