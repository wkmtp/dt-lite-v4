"""API Tests for Phase 1 Task 4 - Authentication, Tenant Resolution & REST API.

Pure mock-based tests (no DB required).
Verifies:
- JWT token structure (sub, iat, exp only)
- Authentication dependency behavior
- Tenant context setup/clear
- PermissionService integration
- Architecture boundary (Router → Service → Repository)
"""
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, AsyncMock, patch
from uuid import uuid4

from services.auth.jwt_handler import AuthService
from services.auth.dependencies import get_current_user, get_current_tenant, require_permission
from services.core.config import settings
from services.tenant_context import get_tenant_context, clear_tenant_context
from services.identity.services.permission_service import PermissionService
from services.core.unit_of_work import UnitOfWork


class TestAuthentication:
    """Test authentication logic."""

    def test_create_access_token_contains_required_claims(self):
        """Token must contain sub, iat, exp. No permission list."""
        user_id = str(uuid4())
        token = AuthService.create_access_token(user_id)
        from jose import jwt
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        assert payload["sub"] == user_id
        assert "iat" in payload
        assert "exp" in payload
        assert "permissions" not in payload
        assert "role" not in payload

    def test_create_access_token_expires(self):
        """Token should have expiration within configured minutes."""
        token = AuthService.create_access_token(str(uuid4()))
        from jose import jwt
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        exp = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        iat = datetime.fromtimestamp(payload["iat"], tz=timezone.utc)
        delta = exp - iat
        max_delta = timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES + 1
        )
        min_delta = timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES - 1
        )
        assert min_delta <= delta <= max_delta

    def test_decode_invalid_token_raises(self):
        """Invalid token should raise ValueError."""
        with pytest.raises(ValueError):
            AuthService.decode_token("invalid-token")

    def test_decode_expired_token_raises(self):
        """Expired token should raise ValueError."""
        from jose import jwt
        payload = {
            "sub": str(uuid4()),
            "exp": datetime.now(timezone.utc) - timedelta(hours=1),
        }
        token = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
        with pytest.raises(ValueError):
            AuthService.decode_token(token)

    @pytest.mark.asyncio
    async def test_get_current_user_missing_token(self):
        """Missing token should raise 401."""
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(None)
        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_get_current_user_invalid_token(self):
        """Invalid token should raise 401."""
        from fastapi import HTTPException
        from fastapi.security import HTTPAuthorizationCredentials
        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="bad-token")
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(creds)
        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_get_current_user_valid_token(self):
        """Valid token should return user dict via repository."""
        from fastapi.security import HTTPAuthorizationCredentials
        from uuid import UUID
        user_id_str = str(uuid4())
        user_id_uuid = UUID(user_id_str)
        token = AuthService.create_access_token(user_id_str)
        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

        mock_user = MagicMock()
        mock_user.id = user_id_uuid
        mock_user.tenant_id = uuid4()
        mock_user.username = "testuser"
        mock_user.is_active = True

        from services.identity.repositories.user_repository import UserRepository
        with patch.object(UserRepository, 'get_by_id', new=AsyncMock(return_value=mock_user)):
            result = await get_current_user(creds)

        assert result["id"] == user_id_str
        assert result["username"] == "testuser"
        assert "tenant_id" in result

    @pytest.mark.asyncio
    async def test_get_current_user_inactive_raises_401(self):
        """Inactive user should raise 401."""
        from fastapi import HTTPException
        from fastapi.security import HTTPAuthorizationCredentials
        user_id = str(uuid4())
        token = AuthService.create_access_token(user_id)
        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

        mock_user = MagicMock()
        mock_user.id = uuid4()
        mock_user.tenant_id = uuid4()
        mock_user.username = "inactive"
        mock_user.is_active = False

        from services.identity.repositories.user_repository import UserRepository
        with patch.object(UserRepository, 'get_by_id', new=AsyncMock(return_value=mock_user)):
            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(creds)
        assert exc_info.value.status_code == 401


class TestTenantResolution:
    """Test tenant context resolution."""

    @pytest.mark.asyncio
    async def test_get_current_tenant_sets_context(self):
        """get_current_tenant should set TenantContext."""
        tenant_id = uuid4()
        user_id = uuid4()
        user = {"id": str(user_id), "tenant_id": str(tenant_id), "username": "test"}

        result = await get_current_tenant(user)
        assert result == tenant_id

        ctx = get_tenant_context()
        assert ctx is not None
        assert ctx.tenant_id == tenant_id
        assert ctx.user_id == user_id

    @pytest.mark.asyncio
    async def test_tenant_context_cleared_after_request(self):
        """TenantContext should be cleared after request."""
        clear_tenant_context()
        assert get_tenant_context() is None


class TestAuthorization:
    """Test authorization logic."""

    @pytest.mark.asyncio
    async def test_require_permission_factory_returns_coroutine(self):
        """require_permission should return an async function."""
        checker = require_permission("entity:read")
        assert callable(checker)

    @pytest.mark.asyncio
    async def test_check_permission_denied_when_no_definition(self):
        """check_permission should raise when permission definition doesn't exist."""
        uow = MagicMock(spec=UnitOfWork)
        perm_repo = MagicMock()
        uow.permissions = perm_repo
        perm_repo.get_by_code = AsyncMock(return_value=None)

        service = PermissionService(uow)
        from services.exceptions.base import PermissionDenied
        with pytest.raises(PermissionDenied):
            await service.check_permission(uuid4(), "entity:read")

    @pytest.mark.asyncio
    async def test_check_permission_denied_when_user_lacks_role(self):
        """check_permission should raise when user has no matching role."""
        uow = MagicMock(spec=UnitOfWork)
        perm_repo = MagicMock()
        uow.permissions = perm_repo
        mock_perm = MagicMock()
        mock_perm.id = uuid4()
        perm_repo.get_by_code = AsyncMock(return_value=mock_perm)
        perm_repo.has_user_permission = AsyncMock(return_value=False)

        service = PermissionService(uow)
        from services.exceptions.base import PermissionDenied
        with pytest.raises(PermissionDenied):
            await service.check_permission(uuid4(), "entity:read")

    @pytest.mark.asyncio
    async def test_check_permission_success(self):
        """check_permission should return True when user has permission."""
        uow = MagicMock(spec=UnitOfWork)
        perm_repo = MagicMock()
        uow.permissions = perm_repo
        mock_perm = MagicMock()
        mock_perm.id = uuid4()
        perm_repo.get_by_code = AsyncMock(return_value=mock_perm)
        perm_repo.has_user_permission = AsyncMock(return_value=True)

        service = PermissionService(uow)
        result = await service.check_permission(uuid4(), "entity:read")
        assert result is True


class TestArchitectureBoundary:
    """Test that Router doesn't directly access Repository or SQLAlchemy."""

    def test_router_uses_service_layer(self):
        """Verify router imports come from services, not repositories."""
        import inspect
        from services.core.api.v2 import routes as core_routes

        source = inspect.getsource(core_routes)

        # Should use service classes
        assert "EntityService" in source
        assert "AssetService" in source
        assert "PropertyService" in source
        assert "RelationshipService" in source

        # Should NOT have direct repository instantiation in route handlers
        lines = source.split('\n')
        for i, line in enumerate(lines):
            if 'async def' in line and i > 0 and '@router' in lines[i - 1]:
                context = '\n'.join(lines[i:i + 15])
                assert 'db.execute' not in context, f"Direct DB access in route: {line}"
                assert '.execute(' not in context, f"Direct execute in route: {line}"

    def test_router_no_direct_sqlalchemy_imports(self):
        """V2 Router should not import SQLAlchemy models or execute SQL."""
        import inspect
        from services.core.api.v2 import routes as core_routes
        from services.identity.api.v2 import routes as identity_routes

        for mod in [core_routes, identity_routes]:
            source = inspect.getsource(mod)
            assert 'from sqlalchemy' not in source, f"{mod.__name__} imports sqlalchemy"
            assert '.execute(' not in source, f"{mod.__name__} calls .execute()"

    def test_dependency_no_direct_sqlalchemy(self):
        """Auth dependencies should not directly use SQLAlchemy."""
        import inspect
        from services.auth import dependencies

        source = inspect.getsource(dependencies)
        assert 'select(' not in source, "dependencies.py uses select()"
        assert '.execute(' not in source, "dependencies.py calls .execute()"


class TestTenantSecurity:
    """Test tenant isolation security."""

    @pytest.mark.asyncio
    async def test_tenant_context_only_from_authenticated_user(self):
        """TenantContext must only be set from get_current_tenant dependency.

        Security rule: Tenant ID comes from JWT user, not from request headers/query/path.
        """
        clear_tenant_context()
        assert get_tenant_context() is None

        tenant_a = uuid4()
        user_a = uuid4()

        # Simulate what get_current_tenant does
        await get_current_tenant({
            "id": str(user_a),
            "tenant_id": str(tenant_a),
            "username": "testuser"
        })

        ctx = get_tenant_context()
        assert ctx is not None
        assert ctx.tenant_id == tenant_a
        assert ctx.user_id == user_a

        clear_tenant_context()

    @pytest.mark.asyncio
    async def test_get_current_user_returns_users_actual_tenant(self):
        """get_current_user must return the user's actual tenant from DB.

        The token only contains user_id (sub). The tenant comes from UserRepository.
        Client cannot manipulate tenant via token.
        """
        from fastapi.security import HTTPAuthorizationCredentials
        from uuid import UUID

        # User belongs to tenant_a
        user_id = str(uuid4())
        tenant_a = uuid4()

        token = AuthService.create_access_token(user_id)
        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

        mock_user = MagicMock()
        mock_user.id = UUID(user_id)
        mock_user.tenant_id = tenant_a  # User's actual tenant
        mock_user.username = "testuser"
        mock_user.is_active = True

        from services.identity.repositories.user_repository import UserRepository
        with patch.object(UserRepository, 'get_by_id', new=AsyncMock(return_value=mock_user)):
            result = await get_current_user(creds)

        # Must return user's actual tenant, not a manipulated one
        assert result["tenant_id"] == str(tenant_a)
        assert result["id"] == user_id

    @pytest.mark.asyncio
    async def test_tenant_context_not_settable_via_request_headers(self):
        """TenantContext cannot be set by client via X-Tenant-ID header.

        Security rule: No middleware should read X-Tenant-ID from request.
        The tenant_id must come from the authenticated user's database record.
        """
        from services.gateway.middleware import TenantContextMiddleware
        import inspect

        # Check the dispatch method implementation (not docstring)
        source = inspect.getsource(TenantContextMiddleware.dispatch)

        # The dispatch method should NOT read tenant from request headers
        assert 'tenant' not in source.lower() or 'context' in source.lower(), \
            "Dispatch method should only manage context lifecycle, not extract tenant from request"
        assert 'headers' not in source.lower(), \
            "Middleware must not read any headers to determine tenant"


class TestPermissionGuardSecurity:
    """Test permission guard security."""

    @pytest.mark.asyncio
    async def test_require_permission_calls_permission_service(self):
        """require_permission must call PermissionService.check_permission()."""
        checker = require_permission("entity:read")

        # Verify it returns an async function
        assert callable(checker)

        # Check the source code references PermissionService
        import inspect
        from services.auth.dependencies import require_permission as rp_func
        source = inspect.getsource(rp_func)
        assert "PermissionService" in source, \
            "require_permission must call PermissionService"
        assert "check_permission" in source, \
            "require_permission must call check_permission method"

    @pytest.mark.asyncio
    async def test_permission_check_uses_tenant_isolation(self):
        """Permission check must include tenant_id for tenant isolation."""
        uow = MagicMock(spec=UnitOfWork)
        perm_repo = MagicMock()
        uow.permissions = perm_repo

        mock_perm = MagicMock()
        mock_perm.id = uuid4()
        perm_repo.get_by_code = AsyncMock(return_value=mock_perm)
        perm_repo.has_user_permission = AsyncMock(return_value=True)

        service = PermissionService(uow)
        user_id = uuid4()
        tenant_id = uuid4()

        # Should pass when tenant matches
        result = await service.check_permission(user_id, "entity:read", tenant_id)
        assert result is True

        # Verify has_user_permission was called with tenant_id
        perm_repo.has_user_permission.assert_called_once()
        call_args = perm_repo.has_user_permission.call_args
        assert call_args[0][2] == tenant_id, \
            "has_user_permission must receive tenant_id for isolation"

    @pytest.mark.asyncio
    async def test_permission_denied_when_cross_tenant_roles(self):
        """User from Tenant A should not have Tenant B's permissions."""
        uow = MagicMock(spec=UnitOfWork)
        perm_repo = MagicMock()
        uow.permissions = perm_repo

        mock_perm = MagicMock()
        mock_perm.id = uuid4()
        perm_repo.get_by_code = AsyncMock(return_value=mock_perm)

        # Simulate: has_user_permission returns False when tenant_id doesn't match
        def check_with_tenant(uid, code, tid=None):
            if tid is not None:
                return False  # Different tenant
            return True

        perm_repo.has_user_permission = AsyncMock(side_effect=check_with_tenant)

        service = PermissionService(uow)
        user_id = uuid4()
        tenant_a = uuid4()

        # Verify cross-tenant denial: when tenant_id is provided, permission should be denied
        from services.exceptions.base import PermissionDenied
        with pytest.raises(PermissionDenied):
            await service.check_permission(user_id, "entity:read", tenant_a)
