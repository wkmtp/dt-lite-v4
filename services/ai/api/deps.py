"""FastAPI dependency injection for AI API endpoints.

R2: All API endpoints require JWT auth + permission check.
"""

from __future__ import annotations

from typing import Optional
from uuid import UUID

from fastapi import Depends, HTTPException, Query, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from services.auth.jwt_handler import AuthService
from services.identity.repositories.user_repository import UserRepository
from services.identity.services.permission_service import PermissionService
from services.core.unit_of_work import UnitOfWork
from services.tenant_context import TenantContext, set_tenant_context
from services.database import AsyncSessionLocal
from services.ai.model.quota import TenantQuotaManager
from services.ai.model.health import HealthChecker
from services.ai.model.gateway import ModelGateway
from services.ai.audit.logger import AuditLogger
from services.ai.model.cost import CostTracker
from services.exceptions.base import PermissionDenied


# -- Global singletons (populated in lifespan) --
_quota_manager: Optional[TenantQuotaManager] = None
_health_checker: Optional[HealthChecker] = None
_gateway: Optional[ModelGateway] = None
_cost_tracker: Optional[CostTracker] = None
_audit_logger: Optional[AuditLogger] = None


def set_gateway(gw: ModelGateway) -> None:
    global _gateway
    _gateway = gw


def get_gateway() -> ModelGateway:
    if _gateway is None:
        raise RuntimeError("ModelGateway not initialized — call lifespan first")
    return _gateway


def set_quota_manager(qm: TenantQuotaManager) -> None:
    global _quota_manager
    _quota_manager = qm


def get_quota_manager() -> TenantQuotaManager:
    if _quota_manager is None:
        raise RuntimeError("TenantQuotaManager not initialized")
    return _quota_manager


def set_health_checker(hc: HealthChecker) -> None:
    global _health_checker
    _health_checker = hc


def get_health_checker() -> HealthChecker:
    if _health_checker is None:
        raise RuntimeError("HealthChecker not initialized")
    return _health_checker


def set_cost_tracker(ct: CostTracker) -> None:
    global _cost_tracker
    _cost_tracker = ct


def get_cost_tracker() -> CostTracker:
    if _cost_tracker is None:
        raise RuntimeError("CostTracker not initialized")
    return _cost_tracker


def set_audit_logger(al: AuditLogger) -> None:
    global _audit_logger
    _audit_logger = al


def get_audit_logger() -> AuditLogger:
    if _audit_logger is None:
        raise RuntimeError("AuditLogger not initialized")
    return _audit_logger


# ---------------------------------------------------------------- auth deps
security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> dict:
    """Validate JWT, return user dict: {id, tenant_id, username, roles}."""
    if credentials is None or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "NOT_AUTHENTICATED", "message": "Authentication required"},
        )
    try:
        payload = AuthService.decode_token(credentials.credentials)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "INVALID_TOKEN", "message": "Invalid or expired token"},
        )
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "INVALID_TOKEN", "message": "Token missing 'sub' claim"},
        )
    async with AsyncSessionLocal() as db:
        user_repo = UserRepository(db)
        user = await user_repo.get_by_id(UUID(user_id))
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "USER_NOT_FOUND", "message": "User not found or inactive"},
        )
    return {
        "id": str(user.id),
        "tenant_id": str(user.tenant_id),
        "username": user.username,
        "roles": [r.role_code for r in user.roles] if hasattr(user, "roles") else [],
    }


async def get_current_tenant(
    user: dict = Depends(get_current_user),
) -> UUID:
    """Set TenantContext and return tenant UUID."""
    tenant_id = UUID(user["tenant_id"])
    ctx = TenantContext(
        tenant_id=tenant_id,
        user_id=UUID(user["id"]),
        user_roles=user.get("roles", []),
    )
    set_tenant_context(ctx)
    return tenant_id


def require_ai_permission(permission_code: str):
    """Dependency factory: checks AI-specific permission (R2)."""
    async def _check(user: dict = Depends(get_current_user)) -> bool:
        tenant_id = UUID(user["tenant_id"])
        user_id = UUID(user["id"])
        async with AsyncSessionLocal() as db:
            uow = UnitOfWork(db)
            perm_service = PermissionService(uow)
            try:
                await perm_service.check_permission(user_id, permission_code, tenant_id)
            except PermissionDenied:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={"code": "PERMISSION_DENIED", "message": f"Missing permission: {permission_code}"},
                )
        return True
    return _check


def require_admin_permission(permission_code: str = "ai:admin"):
    """Dependency for admin endpoints: checks either ai:admin or tenant admin role."""
    async def _check(user: dict = Depends(get_current_user)) -> bool:
        roles = user.get("roles", [])
        if "tenant_admin" in roles or "super_admin" in roles:
            return True
        tenant_id = UUID(user["tenant_id"])
        user_id = UUID(user["id"])
        async with AsyncSessionLocal() as db:
            uow = UnitOfWork(db)
            perm_service = PermissionService(uow)
            try:
                await perm_service.check_permission(user_id, permission_code, tenant_id)
            except PermissionDenied:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={"code": "PERMISSION_DENIED", "message": f"Admin permission required: {permission_code}"},
                )
        return True
    return _check
