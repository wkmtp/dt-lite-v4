"""RoleService - Domain application service for Role management.

Responsible for:
- Role creation within tenant
- Role assignment/removal from users
- Domain event preparation
"""
from uuid import UUID

from services.core.unit_of_work import UnitOfWork
from services.exceptions.base import ValidationError
from services.identity.models.models import Role


class RoleService:
    """Domain service for Role operations.

    Uses repositories exclusively - no direct SQL in service layer.
    """

    def __init__(self, uow: UnitOfWork):
        self._uow = uow

    async def create_role(
        self,
        name: str,
        code: str,
        tenant_id: UUID,
    ) -> dict:
        """Create a new role within a tenant.

        Validates:
        - name and code are non-empty
        - code is unique within tenant
        """
        if not name or not name.strip():
            raise ValidationError(field="name", message="Role name is required")

        if not code or not code.strip():
            raise ValidationError(field="code", message="Role code is required")

        # Check uniqueness using repository
        existing = await self._uow.roles.get_by_code(code.strip(), tenant_id)
        if existing is not None:
            raise ValidationError(
                field="code",
                message=f"Role code '{code}' already exists in this tenant"
            )

        role = Role(
            tenant_id=tenant_id,
            name=name.strip(),
            code=code.strip(),
        )
        role = await self._uow.roles.create(role)
        await self._uow.commit()

        return {
            "id": str(role.id),
            "tenant_id": str(role.tenant_id),
            "name": role.name,
            "code": role.code,
        }

    async def assign_role(self, user_id: UUID, role_id: UUID) -> bool:
        """Assign a role to a user."""
        from services.identity.repositories.role_repository import RoleRepository
        repo = RoleRepository(self._uow.session)
        assigned = await repo.assign_role(user_id, role_id)
        if assigned:
            await self._uow.commit()
        return assigned

    async def remove_role(self, user_id: UUID, role_id: UUID) -> bool:
        """Remove a role from a user."""
        from services.identity.repositories.role_repository import RoleRepository
        repo = RoleRepository(self._uow.session)
        removed = await repo.remove_role(user_id, role_id)
        if removed:
            await self._uow.commit()
        return removed

    async def get_user_roles(self, user_id: UUID) -> list[dict]:
        """Get all roles assigned to a user."""
        from services.identity.repositories.role_repository import RoleRepository
        repo = RoleRepository(self._uow.session)
        roles = await repo.get_user_roles(user_id)
        return [{"id": str(r.id), "name": r.name, "code": r.code} for r in roles]
