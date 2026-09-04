"""PermissionService - Domain application service for permission checks.

Responsible for:
- Permission validation (check if user has required permission)
- Role-to-permission resolution
- Entry point for authorization decisions
"""
from typing import Optional
from uuid import UUID

from services.exceptions.base import PermissionDenied


class PermissionService:
    """Domain service for permission operations.

    This is the single entry point for permission checks in the service layer.
    All authorization decisions flow through this service via repositories.
    """

    def __init__(self, uow):
        self._uow = uow

    async def check_permission(
        self,
        user_id: UUID,
        permission_code: str,
        tenant_id: Optional[UUID] = None,
    ) -> bool:
        """Check if a user has a specific permission.

        Business semantics:
        - The permission definition must exist (global lookup)
        - The user must hold a Role in the same Tenant
        - That Role must be linked to the Permission via RolePermission

        Tenant isolation:
        - If tenant_id is provided, only roles belonging to that tenant are checked.
        - A User in Tenant A cannot inherit permissions from a Role in Tenant B.
        - Permission definitions themselves are global (shared across tenants).

        Args:
            user_id: The user to check
            permission_code: The permission code to verify (e.g., "entity:read")
            tenant_id: Optional tenant filter for tenant-scoped role lookup

        Returns:
            True if the user has the permission

        Raises:
            PermissionDenied: If the permission does not exist or user lacks it
        """
        perm_repo = self._uow.permissions

        # Verify the permission definition exists
        permission = await perm_repo.get_by_code(permission_code)
        if permission is None:
            raise PermissionDenied(permission_code, str(user_id))

        # Check user actually holds this permission through their roles (with tenant isolation)
        has = await perm_repo.has_user_permission(user_id, permission_code, tenant_id)
        if not has:
            raise PermissionDenied(permission_code, str(user_id))

        return True

    async def check_permissions(
        self,
        user_id: UUID,
        required_permissions: list[str],
        tenant_id: Optional[UUID] = None,
    ) -> bool:
        """Check if user has ALL required permissions.

        Args:
            user_id: The user to check
            required_permissions: List of permission codes required
            tenant_id: Optional tenant filter

        Returns:
            True if user has all required permissions

        Raises:
            PermissionDenied: If any permission is missing
        """
        for perm_code in required_permissions:
            has_perm = await self.check_permission(user_id, perm_code, tenant_id)
            if not has_perm:
                raise PermissionDenied(perm_code, str(user_id))
        return True

    async def get_user_permissions(
        self, user_id: UUID, tenant_id: Optional[UUID] = None
    ) -> list[str]:
        """Get all permission codes assigned to a user via their roles.

        Respects tenant isolation: if tenant_id is given, only roles
        belonging to that tenant are considered.
        """
        perm_repo = self._uow.permissions
        return await perm_repo.get_user_permission_codes(user_id, tenant_id)

    async def has_permission(
        self,
        user_id: UUID,
        permission_code: str,
        tenant_id: Optional[UUID] = None,
    ) -> bool:
        """Check permission without raising exception (returns bool)."""
        try:
            await self.check_permission(user_id, permission_code, tenant_id)
            return True
        except PermissionDenied:
            return False
