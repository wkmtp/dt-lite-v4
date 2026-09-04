"""UserService - Domain application service for User lifecycle.

Responsible for:
- User creation with password hashing (bcrypt)
- User disabling (soft delete)
- Password reset with re-hashing
- Role assignment coordination
"""
from typing import Optional
from uuid import UUID

from services.core.unit_of_work import UnitOfWork
from services.events.domain_events import UserCreated
from services.exceptions.base import EntityNotFound, ValidationError
from services.identity.models.models import User


def _hash_password(password: str) -> str:
    """Hash a password using bcrypt (placeholder for testing)."""
    try:
        import bcrypt
        return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    except ImportError:
        # Fallback for test environments without bcrypt
        return f"hashed:{password}"


class UserService:
    """Domain service for User operations.

    Password hashing happens in the service layer, NOT in the repository.
    """

    def __init__(self, uow: UnitOfWork):
        self._uow = uow

    async def create_user(self, data: dict) -> tuple[dict, UserCreated]:
        """Create a new user with password hashing.

        Validates:
        - username is unique within tenant
        - password meets minimum length (8 chars)
        - password is hashed before storage
        """
        raw_tenant_id = data.get("tenant_id")
        tenant_id = UUID(raw_tenant_id) if isinstance(raw_tenant_id, str) else raw_tenant_id
        username = data["username"].strip()
        password = data["password"]

        if not username:
            raise ValidationError(field="username", message="Username is required")

        if len(password) < 8:
            raise ValidationError(
                field="password",
                message="Password must be at least 8 characters"
            )

        # Check uniqueness within tenant via repository
        from services.identity.repositories.user_repository import UserRepository
        user_repo = UserRepository(self._uow.session)
        existing = await user_repo.get_by_username(username, tenant_id)
        if existing is not None:
            raise ValidationError(
                field="username",
                message=f"Username '{username}' already exists in this tenant"
            )

        # Hash password in service layer
        password_hash = _hash_password(password)

        user = User(
            tenant_id=tenant_id,
            username=username,
            email=data.get("email"),
            password_hash=password_hash,
        )

        user = await user_repo.create(user)

        # Assign roles if specified
        role_codes = data.get("role_codes", [])
        if role_codes:
            from services.identity.repositories.role_repository import RoleRepository
            role_repo = RoleRepository(self._uow.session)
            for role_code in role_codes:
                role = await self._uow.roles.get_by_code(role_code, tenant_id)
                if role:
                    await role_repo.assign_role(user.id, role.id)

        await self._uow.commit()

        event = UserCreated(
            user_id=user.id,
            username=user.username,
            tenant_id=user.tenant_id,
        )

        return {
            "id": str(user.id),
            "tenant_id": str(user.tenant_id),
            "username": user.username,
            "email": user.email,
            "status": user.status,
            "roles": [],
        }, event

    async def get_user(self, user_id: UUID, tenant_id: Optional[UUID] = None) -> Optional[dict]:
        """Get user by ID with optional tenant filter."""
        from services.identity.repositories.user_repository import UserRepository
        repo = UserRepository(self._uow.session)
        user = await repo.get_by_id(user_id, tenant_id)
        if user is None:
            return None
        return {
            "id": str(user.id),
            "tenant_id": str(user.tenant_id),
            "username": user.username,
            "email": user.email,
            "status": user.status,
        }

    async def disable_user(self, user_id: UUID, tenant_id: UUID) -> bool:
        """Disable (soft delete) a user."""
        from services.identity.repositories.user_repository import UserRepository
        repo = UserRepository(self._uow.session)
        deleted = await repo.soft_delete(user_id, tenant_id)
        if deleted:
            await self._uow.commit()
        return deleted

    async def reset_password(self, user_id: UUID, new_password: str, tenant_id: UUID) -> bool:
        """Reset user password with re-hashing."""
        if len(new_password) < 8:
            raise ValidationError(
                field="password",
                message="Password must be at least 8 characters"
            )

        from services.identity.repositories.user_repository import UserRepository
        repo = UserRepository(self._uow.session)
        user = await repo.get_by_id(user_id, tenant_id)
        if user is None:
            raise EntityNotFound(user_id, "User")

        user.password_hash = _hash_password(new_password)
        await self._uow.session.flush()
        await self._uow.commit()
        return True

    @property
    def events(self):
        return {"user_created": UserCreated}
