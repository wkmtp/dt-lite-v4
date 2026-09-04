"""PermissionService Tests for Phase 1 Task 3 - Final Semantic Fix."""
import pytest
from unittest.mock import MagicMock, AsyncMock
from uuid import uuid4

from services.core.unit_of_work import UnitOfWork
from services.identity.services.permission_service import PermissionService
from services.exceptions.base import PermissionDenied


class TestPermissionService:
    """Test PermissionService business semantics."""

    def _make_mock_uow(self):
        """Create a mock UoW with mocked permissions repository."""
        uow = MagicMock(spec=UnitOfWork)
        perm_repo = MagicMock()
        uow.permissions = perm_repo
        return uow, perm_repo

    @pytest.mark.asyncio
    async def test_check_permission_user_has_it_via_role(self):
        """Test 1: User拥有权限 → check_permission() 返回 True"""
        uow, perm_repo = self._make_mock_uow()

        mock_permission = MagicMock()
        mock_permission.id = uuid4()
        perm_repo.get_by_code = AsyncMock(return_value=mock_permission)
        perm_repo.has_user_permission = AsyncMock(return_value=True)

        service = PermissionService(uow)
        result = await service.check_permission(
            user_id=uuid4(), permission_code="entity:read"
        )
        assert result is True
        perm_repo.get_by_code.assert_called_once_with("entity:read")
        perm_repo.has_user_permission.assert_called_once()

    @pytest.mark.asyncio
    async def test_check_permission_user_lacks_it_via_role(self):
        """Test 2: 用户没有权限 → PermissionDenied"""
        uow, perm_repo = self._make_mock_uow()

        mock_permission = MagicMock()
        mock_permission.id = uuid4()
        perm_repo.get_by_code = AsyncMock(return_value=mock_permission)
        perm_repo.has_user_permission = AsyncMock(return_value=False)

        service = PermissionService(uow)
        with pytest.raises(PermissionDenied):
            await service.check_permission(
                user_id=uuid4(), permission_code="entity:delete"
            )

    @pytest.mark.asyncio
    async def test_check_permission_definition_not_exists(self):
        """Test 3: 权限定义不存在 → PermissionDenied"""
        uow, perm_repo = self._make_mock_uow()

        perm_repo.get_by_code = AsyncMock(return_value=None)

        service = PermissionService(uow)
        with pytest.raises(PermissionDenied):
            await service.check_permission(
                user_id=uuid4(), permission_code="nonexistent:perm"
            )
        # has_user_permission should NOT be called when definition doesn't exist
        perm_repo.has_user_permission.assert_not_called()

    @pytest.mark.asyncio
    async def test_tenant_isolation_user_cannot_use_other_tenant_roles(self):
        """Test 4: Tenant A 用户不能使用 Tenant B 角色获得权限"""
        uow, perm_repo = self._make_mock_uow()

        tenant_a = uuid4()
        tenant_b = uuid4()
        user_id = uuid4()

        mock_permission = MagicMock()
        mock_permission.id = uuid4()
        perm_repo.get_by_code = AsyncMock(return_value=mock_permission)

        # User in tenant_a has roles → True; tenant_b does not → False
        def _has_perm(uid, code, tid=None):
            return tid == tenant_a
        perm_repo.has_user_permission = AsyncMock(side_effect=_has_perm)

        service = PermissionService(uow)

        # Request from tenant_a — user has the permission
        await service.check_permission(user_id, "entity:read", tenant_a)

        # Request from tenant_b — should deny (tenant isolation)
        with pytest.raises(PermissionDenied):
            await service.check_permission(user_id, "entity:read", tenant_b)

        # Verify has_user_permission was called with correct tenant_id
        calls = perm_repo.has_user_permission.call_args_list
        assert len(calls) == 2
        assert calls[0][0][0] == user_id       # user_id
        assert calls[0][0][2] == tenant_a      # tenant_id for first call
        assert calls[1][0][0] == user_id       # same user
        assert calls[1][0][2] == tenant_b      # different tenant

    @pytest.mark.asyncio
    async def test_get_user_permissions_returns_only_users_permissions(self):
        """Test 5: get_user_permissions() 只返回该用户实际拥有的权限"""
        uow, perm_repo = self._make_mock_uow()

        perm_repo.get_user_permission_codes = AsyncMock(
            return_value=["entity:read", "asset:create"]
        )

        service = PermissionService(uow)
        user_id = uuid4()
        perms = await service.get_user_permissions(user_id)

        assert perms == ["entity:read", "asset:create"]
        perm_repo.get_user_permission_codes.assert_called_once_with(user_id, None)

    @pytest.mark.asyncio
    async def test_different_users_have_different_permissions(self):
        """Test 6: 不同用户拥有不同权限时结果正确"""
        uow, perm_repo = self._make_mock_uow()

        # User A 只能读，User B 能读写
        perm_repo.get_user_permission_codes = AsyncMock(
            side_effect=[
                ["entity:read"],           # user_a
                ["entity:read", "entity:delete"],  # user_b
            ]
        )
        # Both users have entity:read
        mock_perm = MagicMock()
        mock_perm.id = uuid4()
        perm_repo.get_by_code = AsyncMock(return_value=mock_perm)
        perm_repo.has_user_permission = AsyncMock(return_value=True)

        service = PermissionService(uow)
        user_a = uuid4()
        user_b = uuid4()

        perms_a = await service.get_user_permissions(user_a)
        perms_b = await service.get_user_permissions(user_b)

        assert perms_a == ["entity:read"]
        assert perms_b == ["entity:read", "entity:delete"]

    @pytest.mark.asyncio
    async def test_check_permissions_multiple_required(self):
        """Test: check_permissions with multiple required permissions."""
        uow, perm_repo = self._make_mock_uow()

        mock_perm = MagicMock()
        mock_perm.id = uuid4()
        perm_repo.get_by_code = AsyncMock(return_value=mock_perm)
        perm_repo.has_user_permission = AsyncMock(return_value=True)

        service = PermissionService(uow)
        result = await service.check_permissions(
            user_id=uuid4(),
            required_permissions=["entity:read", "asset:create"],
        )
        assert result is True

    @pytest.mark.asyncio
    async def test_check_permissions_one_missing_raises(self):
        """Test: check_permissions raises when one permission is missing."""
        uow, perm_repo = self._make_mock_uow()

        mock_perm = MagicMock()
        mock_perm.id = uuid4()
        perm_repo.get_by_code = AsyncMock(return_value=mock_perm)
        # First call returns True, second returns False
        perm_repo.has_user_permission = AsyncMock(
            side_effect=[True, False]
        )

        service = PermissionService(uow)
        with pytest.raises(PermissionDenied):
            await service.check_permissions(
                user_id=uuid4(),
                required_permissions=["entity:read", "asset:create"],
            )

    @pytest.mark.asyncio
    async def test_has_permission_returns_false_on_denied(self):
        """Test: has_permission returns False instead of raising."""
        uow, perm_repo = self._make_mock_uow()

        perm_repo.get_by_code = AsyncMock(return_value=None)

        service = PermissionService(uow)
        result = await service.has_permission(uuid4(), "entity:delete")
        assert result is False
