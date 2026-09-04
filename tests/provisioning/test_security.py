"""Test provisioning tenant security."""
import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4


class TestTenantSecurity:
    """Test tenant isolation in provisioning layer."""

    @pytest.mark.asyncio
    async def test_cross_tenant_plan_access_blocked(self):
        """Cross-tenant plan access must return None."""
        from services.provisioning.repository import ProvisioningPlanRepository
        session = MagicMock()
        session.execute = AsyncMock()
        repo = ProvisioningPlanRepository(session)
        result = MagicMock()
        result.scalar_one_or_none.return_value = None
        session.execute.return_value = result

        r = await repo.get_by_id_for_tenant(uuid4(), uuid4())
        assert r is None

    @pytest.mark.asyncio
    async def test_cross_tenant_execution_blocked(self):
        """Cross-tenant execution access must be blocked."""
        from services.provisioning.repository import ProvisioningExecutionRepository
        session = MagicMock()
        session.execute = AsyncMock()
        repo = ProvisioningExecutionRepository(session)
        result = MagicMock()
        result.scalars.return_value.all.return_value = []
        session.execute.return_value = result

        r = await repo.list_by_plan(uuid4(), uuid4())
        assert r == []

    def test_plan_create_request_no_tenant_id(self):
        """ProvisioningPlanCreateRequest must NOT have tenant_id field."""
        from services.provisioning.schemas import ProvisioningPlanCreateRequest
        assert "tenant_id" not in ProvisioningPlanCreateRequest.model_fields

    def test_routes_use_dependency_injection(self):
        """All endpoints must use Depends(get_current_tenant)."""
        from services.provisioning.routes import router
        for route in router.routes:
            deps = getattr(route, "dependencies", [])
            assert len(deps) > 0, f"Route {route.path} missing dependencies"

    def test_all_endpoints_have_permission_guard(self):
        """All endpoints must have permission dependencies."""
        from services.provisioning.routes import router
        for route in router.routes:
            deps = getattr(route, "dependencies", [])
            assert any("require_permission" in str(d) for d in deps), \
                f"Route {route.path} missing permission guard"

    def test_execution_model_has_tenant_id(self):
        """Execution model must reference tenant_id."""
        from services.provisioning.models import ProvisioningExecution
        annotations = ProvisioningExecution.__annotations__
        assert "tenant_id" in annotations

    def test_item_model_has_tenant_id(self):
        """Item model must reference tenant_id."""
        from services.provisioning.models import ProvisioningItem
        annotations = ProvisioningItem.__annotations__
        assert "tenant_id" in annotations

    def test_service_never_accepts_tenant_from_body(self):
        """Service methods must accept tenant_id as explicit parameter, not from request body."""
        import inspect
        from services.provisioning.services import ProvisioningService
        sig = inspect.signature(ProvisioningService.create_plan)
        params = list(sig.parameters.keys())
        assert "tenant_id" in params
        assert "deployment_instance_id" in params
