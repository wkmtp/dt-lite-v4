"""JWT Authentication dependencies for DT-Lite"""
from datetime import datetime, timedelta
from typing import Optional
import uuid
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from services.database import get_db
from services.core.config import settings
from services.identity.models.models import User, Tenant, UserRole, Role, RolePermission, Permission


security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> User:
    """Extract and validate JWT token, return current user"""
    token = credentials.credentials
    
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token payload")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
    user = result.scalars().first()
    
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")
    
    return user


async def get_current_tenant(
    user: User = Depends(get_current_user)
) -> str:
    """Get tenant_id from current user"""
    return str(user.tenant_id)


def require_permission(permission_code: str):
    """Dependency factory for permission checking"""
    async def permission_checker(
        user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
    ) -> bool:
        # Super admin bypass (in production, check system role)
        roles_result = await db.execute(
            select(Role).join(UserRole, Role.id == UserRole.role_id)
            .where(UserRole.user_id == user.id)
        )
        roles = roles_result.scalars().all()
        
        # Check each role's permissions
        for role in roles:
            perms_result = await db.execute(
                select(Permission.code).join(RolePermission, Permission.id == RolePermission.permission_id)
                .where(RolePermission.role_id == role.id)
            )
            codes = [p[0] for p in perms_result.all()]
            if permission_code in codes:
                return True
        
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Permission denied: {permission_code}"
        )
    return permission_checker
