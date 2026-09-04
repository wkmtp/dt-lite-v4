"""FastAPI Dependencies for Authentication, Tenant Resolution & Authorization.

Architecture:
    Router
      ↓
    get_current_user()          → AuthService + UserRepository
      ↓
    get_current_tenant()        → sets TenantContext, returns UUID
      ↓
    require_permission("...")   → PermissionService
      ↓
    Service (EntityService, etc.)
      ↓
    Repository (only layer that touches DB)

These are designed to be used as FastAPI Depends().
"""
from typing import Optional
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from services.auth.jwt_handler import AuthService
from services.identity.repositories.user_repository import UserRepository
from services.identity.services.permission_service import PermissionService
from services.core.unit_of_work import UnitOfWork
from services.tenant_context import set_tenant_context, TenantContext
from services.database import AsyncSessionLocal
from services.exceptions.base import PermissionDenied

security = HTTPBearer(auto_error=False)


async def get_db():
    """Yield a database session for services that need it directly."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


def _extract_user_id(token: str) -> str:
    """Extract user_id from token payload. Raises 401 on any failure."""
    try:
        payload = AuthService.decode_token(token)
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
    return str(user_id)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> dict:
    """Validate JWT and return user info via UserRepository.

    Returns a dict with keys: id (str), tenant_id (str), username (str).
    Raises 401 for: missing token, invalid token, expired token, inactive user.
    """
    if credentials is None or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "NOT_AUTHENTICATED", "message": "Authentication required"},
        )

    token = credentials.credentials
    user_id = _extract_user_id(token)

    # Look up user through repository — no direct SQLAlchemy in dep layer
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
    }


async def get_current_tenant(
    user: dict = Depends(get_current_user),
) -> UUID:
    """Set TenantContext and return the current user's tenant UUID."""
    tenant_id = UUID(user["tenant_id"])
    ctx = TenantContext(
        tenant_id=tenant_id,
        user_id=UUID(user["id"]),
    )
    set_tenant_context(ctx)
    return tenant_id


def require_permission(permission_code: str):
    """Dependency factory: checks that the current user has a permission.

    Usage:
        @router.get("/entities", dependencies=[Depends(require_permission("entity:read"))])

    Raises 403 (PermissionDenied→HTTPException) if the user lacks the permission.
    Does NOT raise 401 — that is handled by get_current_user.
    """
    async def _check(
        user: dict = Depends(get_current_user),
    ) -> bool:
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
                    detail={
                        "code": "PERMISSION_DENIED",
                        "message": f"Missing permission: {permission_code}",
                    },
                )
        return True

    return _check
