"""User Repository - Manages User domain objects."""
from typing import Optional, Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from services.core.repositories.base import TenantAwareRepository
from services.identity.models.models import User


class UserRepository(TenantAwareRepository[User]):
    """Repository for User domain operations."""

    def __init__(self, session: AsyncSession):
        super().__init__(session, model=User)

    async def get_by_username(self, username: str, tenant_id: UUID) -> Optional[User]:
        """Get user by username within a tenant."""
        stmt = select(User).where(
            User.username == username,
            User.tenant_id == tenant_id,
            User.deleted_at.is_(None)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email (global search)."""
        stmt = select(User).where(
            User.email == email,
            User.deleted_at.is_(None)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_id(self, user_id: UUID, tenant_id: Optional[UUID] = None) -> Optional[User]:
        """Get user by ID."""
        stmt = select(User).where(User.id == user_id)

        if tenant_id:
            stmt = stmt.where(User.tenant_id == tenant_id)

        stmt = stmt.where(User.deleted_at.is_(None))

        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_tenant(
        self,
        tenant_id: UUID,
        limit: int = 20,
        offset: int = 0
    ) -> Sequence[User]:
        """List users within a tenant."""
        stmt = select(User).where(
            User.tenant_id == tenant_id,
            User.deleted_at.is_(None)
        ).offset(offset).limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def create(self, user: User) -> User:
        """Create a new user. Caller must commit."""
        self.session.add(user)
        await self.session.flush()
        await self.session.refresh(user)
        return user

    async def soft_delete(self, user_id: UUID, tenant_id: UUID) -> bool:
        """Soft delete a user."""
        user = await self.get_by_id(user_id, tenant_id)
        if user is None:
            return False

        user.soft_delete()
        await self.session.flush()
        return True
