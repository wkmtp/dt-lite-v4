"""TenantService - Domain application service for Tenant lifecycle.

Responsible for:
- Tenant creation with business rule validation
- Tenant disabling (soft delete)
- Domain event preparation
"""
from typing import Optional
from uuid import UUID

from services.core.unit_of_work import UnitOfWork
from services.events.domain_events import TenantCreated
from services.exceptions.base import EntityNotFound, ValidationError
from services.identity.models.models import Tenant
from services.identity.repositories.tenant_repository import TenantRepository


def _to_response(tenant: Tenant) -> dict:
    """Convert Tenant model to response dict."""
    return {
        "id": str(tenant.id),
        "name": tenant.name,
        "code": tenant.code,
        "status": tenant.status,
        "extra_data": tenant.extra_data,
        "created_at": tenant.created_at.isoformat() if tenant.created_at else None,
        "updated_at": tenant.updated_at.isoformat() if tenant.updated_at else None,
        "deleted_at": tenant.deleted_at.isoformat() if tenant.deleted_at else None,
    }


class TenantService:
    """Domain service for Tenant operations."""

    def __init__(self, uow: UnitOfWork):
        self._uow = uow

    async def create_tenant(self, data: dict) -> tuple[dict, TenantCreated]:
        """Create a new tenant with validation.

        Rules:
        - name must not be empty
        - code must be unique globally
        """
        name = data.get("name", "").strip()
        code = data.get("code", "").strip()

        if not name:
            raise ValidationError(field="name", message="Tenant name is required")

        if not code:
            raise ValidationError(field="code", message="Tenant code is required")

        # Check uniqueness of code via repository
        repo = TenantRepository(self._uow.session)
        existing = await repo.get_by_code(code)
        if existing is not None:
            raise ValidationError(
                field="code",
                message=f"Tenant code '{code}' already exists"
            )

        tenant = Tenant(
            name=name,
            code=code.lower(),
            extra_data=data.get("metadata", {}),
        )

        tenant = await repo.create(tenant)
        await self._uow.commit()

        event = TenantCreated(
            tenant_id=tenant.id,
            tenant_code=tenant.code,
            tenant_name=tenant.name,
        )

        return _to_response(tenant), event

    async def get_tenant(self, tenant_id: UUID) -> Optional[dict]:
        """Get tenant by ID."""
        repo = TenantRepository(self._uow.session)
        tenant = await repo.get_by_id(tenant_id)
        if tenant is None:
            return None
        return _to_response(tenant)

    async def disable_tenant(self, tenant_id: UUID) -> bool:
        """Disable a tenant by soft deletion."""
        repo = TenantRepository(self._uow.session)
        tenant = await repo.get_by_id(tenant_id)
        if tenant is None:
            raise EntityNotFound(tenant_id, "Tenant")

        tenant.soft_delete()
        await self._uow.commit()
        return True

    async def list_tenants(
        self, skip: int = 0, limit: int = 20
    ) -> dict:
        """List all tenants with pagination."""
        repo = TenantRepository(self._uow.session)
        tenants = await repo.list(skip=skip, limit=limit)
        return {
            "items": [_to_response(t) for t in tenants],
            "total": len(tenants),
            "limit": limit,
            "offset": skip,
        }

    @property
    def events(self):
        return {"tenant_created": TenantCreated}
