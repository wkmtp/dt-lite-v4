"""Identity API Routes v2 - Tenant, User management.

All routes go through Service Layer → Repository Layer.
Router never touches SQLAlchemy directly.
"""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from services.auth.dependencies import get_current_tenant, require_permission
from services.core.unit_of_work import UnitOfWork
from services.database import AsyncSessionLocal
from services.exceptions.base import ValidationError
from services.identity.schemas.tenant_v2 import TenantCreate, TenantListResponse, TenantResponse
from services.identity.schemas.user_v2 import UserCreate, UserListResponse, UserResponse
from services.identity.services.tenant_service import TenantService
from services.identity.services.user_service import UserService

router = APIRouter(prefix="/api/v1", tags=["Identity"])


# ==================== TENANT ENDPOINTS ====================

@router.post("/tenants", response_model=TenantResponse, status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(require_permission("tenant:create"))])
async def create_tenant(
    data: TenantCreate,
):
    """Create a new tenant."""
    async with AsyncSessionLocal() as db:
        uow = UnitOfWork(db)
        service = TenantService(uow)
        try:
            tenant, event = await service.create_tenant(data.model_dump())
        except ValidationError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail={"code": e.code, "message": e.message})
    return tenant


@router.get("/tenants", response_model=TenantListResponse,
            dependencies=[Depends(require_permission("tenant:read"))])
async def list_tenants(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
):
    """List all tenants."""
    async with AsyncSessionLocal() as db:
        uow = UnitOfWork(db)
        service = TenantService(uow)
        result = await service.list_tenants(skip, limit)
    return result


# ==================== USER ENDPOINTS ====================

@router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(require_permission("user:create"))])
async def create_user(
    data: UserCreate,
    tenant_id: UUID = Depends(get_current_tenant),
):
    """Create a new user in the current tenant."""
    async with AsyncSessionLocal() as db:
        uow = UnitOfWork(db)
        service = UserService(uow)
        try:
            user, event = await service.create_user(data.model_dump(), tenant_id)
        except ValidationError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail={"code": e.code, "message": e.message})
    return user


@router.get("/users", response_model=UserListResponse,
            dependencies=[Depends(require_permission("user:read"))])
async def list_users(
    tenant_id: UUID = Depends(get_current_tenant),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
):
    """List users in the current tenant."""
    async with AsyncSessionLocal() as db:
        uow = UnitOfWork(db)
        service = UserService(uow)
        result = await service.list_users(tenant_id, skip, limit)
    return result


@router.get("/users/{user_id}", response_model=UserResponse,
            dependencies=[Depends(require_permission("user:read"))])
async def get_user(
    user_id: UUID,
    tenant_id: UUID = Depends(get_current_tenant),
):
    """Get user by ID."""
    async with AsyncSessionLocal() as db:
        uow = UnitOfWork(db)
        service = UserService(uow)
        user = await service.get_user(user_id, tenant_id)
    if user is None:
        detail_msg = {"code": "USER_NOT_FOUND", "message": f"User {user_id} not found"}
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail_msg)
    return user
