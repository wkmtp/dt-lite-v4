"""Repository Pattern for DT-Lite Identity"""
from typing import Optional, List
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, update
from sqlalchemy.orm import selectinload

from services.identity.models.models import Tenant, User, Role, Permission, UserRole, RolePermission


class TenantRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, tenant_id: str) -> Optional[Tenant]:
        result = await self.db.execute(
            select(Tenant).where(Tenant.id == uuid.UUID(tenant_id))
        )
        return result.scalars().first()

    async def get_by_code(self, code: str) -> Optional[Tenant]:
        result = await self.db.execute(
            select(Tenant).where(Tenant.code == code)
        )
        return result.scalars().first()

    async def list(self, skip: int = 0, limit: int = 20) -> List[Tenant]:
        result = await self.db.execute(
            select(Tenant).offset(skip).limit(limit)
        )
        return list(result.scalars().all())

    async def create(self, tenant: Tenant) -> Tenant:
        self.db.add(tenant)
        await self.db.commit()
        await self.db.refresh(tenant)
        return tenant

    async def update(self, tenant_id: str, **kwargs) -> Optional[Tenant]:
        tenant = await self.get_by_id(tenant_id)
        if not tenant:
            return None
        for key, value in kwargs.items():
            if hasattr(tenant, key):
                setattr(tenant, key, value)
        await self.db.commit()
        await self.db.refresh(tenant)
        return tenant

    async def delete(self, tenant_id: str) -> bool:
        result = await self.db.execute(
            delete(Tenant).where(Tenant.id == uuid.UUID(tenant_id))
        )
        await self.db.commit()
        return result.rowcount > 0


class UserRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, user_id: str) -> Optional[User]:
        result = await self.db.execute(
            select(User).options(selectinload(User.roles)).where(User.id == uuid.UUID(user_id))
        )
        return result.scalars().first()

    async def get_by_username_and_tenant(self, username: str, tenant_id: str) -> Optional[User]:
        result = await self.db.execute(
            select(User).join(Tenant).where(
                User.username == username,
                Tenant.code == tenant_id,
                User.status == "active"
            )
        )
        return result.scalars().first()

    async def list_by_tenant(self, tenant_id: str, skip: int = 0, limit: int = 20) -> List[User]:
        result = await self.db.execute(
            select(User).where(User.tenant_id == uuid.UUID(tenant_id)).offset(skip).limit(limit)
        )
        return list(result.scalars().all())

    async def create(self, user: User) -> User:
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def update(self, user_id: str, **kwargs) -> Optional[User]:
        user = await self.get_by_id(user_id)
        if not user:
            return None
        for key, value in kwargs.items():
            if hasattr(user, key):
                setattr(user, key, value)
        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def delete(self, user_id: str) -> bool:
        result = await self.db.execute(delete(User).where(User.id == uuid.UUID(user_id)))
        await self.db.commit()
        return result.rowcount > 0


class RoleRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, role_id: str) -> Optional[Role]:
        result = await self.db.execute(
            select(Role).options(
                selectinload(Role.permissions).joinedload(RolePermission.permission)
            ).where(Role.id == uuid.UUID(role_id))
        )
        return result.scalars().first()

    async def list_by_tenant(self, tenant_id: str) -> List[Role]:
        result = await self.db.execute(
            select(Role).where(Role.tenant_id == uuid.UUID(tenant_id))
        )
        return list(result.scalars().all())

    async def create(self, role: Role) -> Role:
        self.db.add(role)
        await self.db.commit()
        await self.db.refresh(role)
        return role


class PermissionRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_all(self) -> List[Permission]:
        result = await self.db.execute(select(Permission))
        return list(result.scalars().all())

    async def get_codes_by_role(self, role_id: str) -> List[str]:
        result = await self.db.execute(
            select(Permission.code).join(
                RolePermission, Permission.id == RolePermission.permission_id
            ).where(RolePermission.role_id == uuid.UUID(role_id))
        )
        return [row[0] for row in result.all()]
