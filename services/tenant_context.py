"""Tenant Context for multi-tenant isolation.

This module provides the foundation for tenant context propagation across
the request lifecycle. It does NOT modify existing API business logic.

Usage:
    from services.tenant_context import set_tenant_context, get_tenant_id
    
    # In a middleware or dependency (to be integrated in later tasks):
    ctx = TenantContext(tenant_id=uuid4(), user_id=user.id)
    with set_tenant_context(ctx):
        result = await some_operation()  # Uses ctx.tenant_id implicitly
"""
from contextvars import ContextVar
from typing import Optional
import uuid
from dataclasses import dataclass, field


@dataclass
class TenantContext:
    """Holds the current tenant and user context for a request."""
    tenant_id: uuid.UUID
    user_id: Optional[uuid.UUID] = None
    user_roles: list[str] = field(default_factory=list)
    
    @property
    def tenant_id_str(self) -> str:
        return str(self.tenant_id)


# Context variable to store tenant context per async task
_tenant_ctx_var: ContextVar[Optional[TenantContext]] = ContextVar(
    '_tenant_ctx', default=None
)


def get_tenant_context() -> Optional[TenantContext]:
    """Get the current tenant context, or None if not set."""
    return _tenant_ctx_var.get()


def get_tenant_id() -> Optional[str]:
    """Convenience: get current tenant_id as string, or None."""
    ctx = _tenant_ctx_var.get()
    return ctx.tenant_id_str if ctx else None


def set_tenant_context(ctx: TenantContext) -> None:
    """Set the tenant context for the current async task."""
    _tenant_ctx_var.set(ctx)


def clear_tenant_context() -> None:
    """Clear the tenant context for the current async task."""
    _tenant_ctx_var.set(None)
