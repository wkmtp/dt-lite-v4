"""Authentication API Routes.

POST /api/v1/auth/login
GET  /api/v1/auth/me
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from services.auth.schemas import LoginRequest, TokenResponse
from services.auth.dependencies import get_db, get_current_user
from services.identity.services.auth_service import AuthService
from services.core.unit_of_work import UnitOfWork
from services.exceptions.base import ValidationError

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])


@router.post("/login", response_model=TokenResponse)
async def login(
    data: LoginRequest,
    db: AsyncSession = Depends(get_db),
):
    """Authenticate user and return JWT access token.

    Token contains: sub (user_id), iat, exp.
    Does NOT contain permission list.
    """
    # Authenticate via service layer (uses UnitOfWork internally)
    uow = UnitOfWork(db)
    auth_service = AuthService()
    try:
        result = await auth_service.login(uow, data.username, data.password, data.tenant_code)
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": e.code, "message": e.message},
        )

    return TokenResponse(
        access_token=result["access_token"],
        token_type=result["token_type"],
        expires_in=result["expires_in"],
    )


@router.get("/me")
async def get_me(
    user: dict = Depends(get_current_user),
):
    """Get current authenticated user info."""
    return {
        "id": user["id"],
        "username": user["username"],
        "tenant_id": user["tenant_id"],
    }


@router.post("/logout")
async def logout():
    """Logout endpoint (stateless - JWT is invalidated on client side)."""
    return {"success": True, "message": "Logged out"}
