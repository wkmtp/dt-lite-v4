"""Role Repository - Manages Role domain objects."""
from typing import Optional, Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from services.core.repositories.base import TenantAwareRepository
from services.identity.models.models import Role, UserRole


class RoleRepository(TenantAwareRepository[Role]):
    """Repository for Role domain operations."""

    def __init__(self, session: AsyncSession):
        super().__init__(session, model=Role)

    async def get_by_code(self, code: str, tenant_id: UUID) -> Optional[Role]:
        """Get role by code within a tenant."""
        stmt = select(Role).where(
            Role.code == code,
            Role.tenant_id == tenant_id,
            Role.deleted_at.is_(None)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_id(self, role_id: UUID, tenant_id: UUID) -> Optional[Role]:
        """Get role by ID within a tenant."""
        stmt = select(Role).where(
            Role.id == role_id,
            Role.tenant_id == tenant_id,
            Role.deleted_at.is_(None)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_tenant(
        self,
        tenant_id: UUID,
        limit: int = 50,
        offset: int = 0
    ) -> Sequence[Role]:
        """List roles within a tenant."""
        stmt = select(Role).where(
            Role.tenant_id == tenant_id,
            Role.deleted_at.is_(None)
        ).offset(offset).limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def assign_role(self, user_id: UUID, role_id: UUID) -> bool:
        """Assign a role to a user."""
        # Check if assignment already exists
        stmt = select(UserRole).where(
            UserRole.user_id == user_id,
            UserRole.role_id == role_id
        )
        result = await self.session.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing:
            return False

        user_role = UserRole(user_id=user_id, role_id=role_id)
        self.session.add(user_role)
        await self.session.flush()
        return True

    async def remove_role(self, user_id: UUID, role_id: UUID) -> bool:
        """Remove a role from a user."""
        stmt = select(UserRole).where(
            UserRole.user_id == user_id,
            UserRole.role_id == role_id
        )
        result = await self.session.execute(stmt)
        user_role = result.scalar_one_or_none()

        if user_role:
            await self.session.delete(user_role)
            await self.session.flush()
            return True
        return False

    async def get_user_roles(self, user_id: UUID) -> Sequence[Role]:
        """Get all roles assigned to a user."""
        stmt = (
            select(Role)
            .join(UserRole, Role.id == UserRole.role_id)
            .where(UserRole.user_id == user_id)
            .where(Role.deleted_at.is_(None))
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def create(self, role: Role) -> Role:
        """Create a new role. Caller must commit."""
        self.session.add(role)
        await self.session.flush()
        await self.session.refresh(role)
        return role

    async def soft_delete(self, role_id: UUID, tenant_id: UUID) -> bool:
        """Soft delete a role."""
        role = await self.get_by_id(role_id, tenant_id)
        if role is None:
            return False

        role.soft_delete()
        await self.session.flush()
        return True
