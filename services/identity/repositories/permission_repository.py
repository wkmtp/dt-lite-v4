"""Permission Repository - Manages Permission domain objects."""
from typing import Optional, Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from services.core.repositories.base import BaseRepository
from services.identity.models.models import Permission, Role, RolePermission, UserRole


class PermissionRepository(BaseRepository[Permission]):
    """Repository for Permission domain operations."""

    def __init__(self, session: AsyncSession):
        super().__init__(session, model=Permission)

    async def get_by_code(self, code: str) -> Optional[Permission]:
        """Get permission by code."""
        stmt = select(Permission).where(
            Permission.code == code,
            Permission.deleted_at.is_(None)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_all(self) -> Sequence[Permission]:
        """List all active permissions."""
        stmt = select(Permission).where(Permission.deleted_at.is_(None))
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_role_ids_for_user(self, user_id: UUID) -> list[UUID]:
        """Get all role IDs assigned to a user (tenant-agnostic; caller must filter by tenant)."""
        stmt = select(UserRole.role_id).where(UserRole.user_id == user_id)
        result = await self.session.execute(stmt)
        return [row[0] for row in result.all()]

    async def get_permission_ids_for_roles(self, role_ids: list[UUID]) -> set[UUID]:
        """Get all permission IDs assigned to a set of roles."""
        if not role_ids:
            return set()
        stmt = select(RolePermission.permission_id).where(
            RolePermission.role_id.in_(role_ids)
        )
        result = await self.session.execute(stmt)
        return {row[0] for row in result.all()}

    async def has_user_permission(
        self,
        user_id: UUID,
        permission_code: str,
        tenant_id: Optional[UUID] = None,
    ) -> bool:
        """Check if a user has a specific permission, with tenant isolation.

        Query path:
          User --(UserRole)--> Role(tenant_id=X) --(RolePermission)--> Permission

        If tenant_id is provided, the Role must belong to that tenant.
        Permission definition is global (not tenant-scoped), but the Role
        assignment is tenant-isolated.
        """
        # Step 1: Get user's role IDs
        role_ids = await self.get_role_ids_for_user(user_id)
        if not role_ids:
            return False

        # Step 2: Filter roles by tenant if specified
        stmt = select(Role.id).where(
            Role.id.in_(role_ids),
            Role.deleted_at.is_(None)
        )
        if tenant_id:
            stmt = stmt.where(Role.tenant_id == tenant_id)
        result = await self.session.execute(stmt)
        tenant_role_ids = [row[0] for row in result.all()]

        if not tenant_role_ids:
            return False

        # Step 3: Get permission IDs for those roles
        perm_ids = await self.get_permission_ids_for_roles(tenant_role_ids)
        if not perm_ids:
            return False

        # Step 4: Check if the target permission is in the set
        perm_stmt = select(Permission.id).where(
            Permission.id.in_(perm_ids),
            Permission.code == permission_code,
            Permission.deleted_at.is_(None)
        )
        perm_result = await self.session.execute(perm_stmt)
        return perm_result.scalar_one_or_none() is not None

    async def get_user_permission_codes(
        self,
        user_id: UUID,
        tenant_id: Optional[UUID] = None,
    ) -> list[str]:
        """Get all permission codes assigned to a user, with tenant isolation."""
        # Step 1: Get user's role IDs
        role_ids = await self.get_role_ids_for_user(user_id)
        if not role_ids:
            return []

        # Step 2: Filter by tenant if specified
        stmt = select(Role.id).where(
            Role.id.in_(role_ids),
            Role.deleted_at.is_(None)
        )
        if tenant_id:
            stmt = stmt.where(Role.tenant_id == tenant_id)
        result = await self.session.execute(stmt)
        tenant_role_ids = [row[0] for row in result.all()]

        if not tenant_role_ids:
            return []

        # Step 3: Get permissions through RolePermission
        perm_ids = await self.get_permission_ids_for_roles(tenant_role_ids)
        if not perm_ids:
            return []

        stmt = select(Permission.code).where(
            Permission.id.in_(perm_ids),
            Permission.deleted_at.is_(None)
        )
        result = await self.session.execute(stmt)
        return [row[0] for row in result.all()]
