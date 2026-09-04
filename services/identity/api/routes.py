"""FastAPI Router for Identity endpoints - Tenant, User, Auth"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from services.database import get_db
from services.identity.services.auth_service import AuthService
from services.identity.repositories import TenantRepository, UserRepository
from services.identity.schemas.tenant import TenantCreate, TenantUpdate
from services.identity.schemas.user import UserCreate, UserResponse, LoginRequest, TokenResponse
from services.identity.models.models import Tenant, User

router = APIRouter(prefix="/api/v1/identity", tags=["Identity"])


@router.get("/health")
async def health_check():
    return {"status": "ok"}


# ========== Tenant Endpoints ==========

@router.post("/tenants", response_model=dict)
async def create_tenant(
    data: TenantCreate,
    db: AsyncSession = Depends(get_db)
):
    repo = TenantRepository(db)
    existing = await repo.get_by_code(data.code)
    if existing:
        raise HTTPException(status_code=400, detail={"code": "TENANT_CODE_EXISTS", "message": "Tenant code already exists"})
    
    tenant = Tenant(
        id=__import__('uuid').uuid4(),
        name=data.name,
        code=data.code,
        status="active",
        extra_data=data.metadata,
    )
    tenant = await repo.create(tenant)
    return {
        "success": True,
        "data": {
            "id": str(tenant.id),
            "name": tenant.name,
            "code": tenant.code,
            "status": tenant.status,
        }
    }


@router.get("/tenants", response_model=dict)
async def list_tenants(
    skip: int = 0,
    limit: int = 20,
    db: AsyncSession = Depends(get_db)
):
    repo = TenantRepository(db)
    tenants = await repo.list(skip=skip, limit=limit)
    return {
        "success": True,
        "data": [
            {
                "id": str(t.id),
                "name": t.name,
                "code": t.code,
                "status": t.status,
                "created_at": t.created_at.isoformat(),
            }
            for t in tenants
        ],
        "meta": {"total": len(tenants)}
    }


# ========== Auth Endpoints ==========

@router.post("/auth/login", response_model=dict)
async def login(
    data: LoginRequest,
    db: AsyncSession = Depends(get_db)
):
    auth_service = AuthService()
    try:
        result = await auth_service.login(db, data.username, data.password, data.tenant_code)
        return result
    except ValueError:
        raise HTTPException(status_code=401, detail={"code": "INVALID_CREDENTIALS", "message": "Invalid credentials"})


@router.post("/auth/logout")
async def logout():
    return {"success": True, "message": "Logged out"}


@router.get("/auth/me")
async def get_me(
    user_id: str,
    db: AsyncSession = Depends(get_db)
):
    auth_service = AuthService()
    profile = await auth_service.get_user_profile(db, user_id)
    if not profile:
        raise HTTPException(status_code=404, detail={"code": "USER_NOT_FOUND", "message": "User not found"})
    return {"success": True, "data": profile}


# ========== User Endpoints ==========

@router.post("/users", response_model=dict)
async def create_user(
    data: UserCreate,
    db: AsyncSession = Depends(get_db)
):
    repo = UserRepository(db)
    auth_service = AuthService()
    
    # Check if username already exists in tenant
    existing = await repo.get_by_username_and_tenant(data.username, data.tenant_id)
    if existing:
        raise HTTPException(status_code=400, detail={"code": "USERNAME_EXISTS", "message": "Username already exists"})
    
    user = User(
        id=__import__('uuid').uuid4(),
        tenant_id=__import__('uuid').UUID(data.tenant_id),
        username=data.username,
        email=data.email,
        password_hash=auth_service.hash_password(data.password),
        status="active",
    )
    user = await repo.create(user)
    return {
        "success": True,
        "data": {
            "id": str(user.id),
            "username": user.username,
            "email": user.email,
            "tenant_id": str(user.tenant_id),
        }
    }


@router.get("/users", response_model=dict)
async def list_users(
    tenant_id: str,
    skip: int = 0,
    limit: int = 20,
    db: AsyncSession = Depends(get_db)
):
    repo = UserRepository(db)
    users = await repo.list_by_tenant(tenant_id, skip=skip, limit=limit)
    return {
        "success": True,
        "data": [
            {
                "id": str(u.id),
                "username": u.username,
                "email": u.email,
                "status": u.status,
                "created_at": u.created_at.isoformat(),
            }
            for u in users
        ]
    }
