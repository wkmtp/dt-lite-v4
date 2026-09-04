"""Authentication Service - Handles login with proper architecture.

Architecture:
- Uses Repositories for all DB access (no direct SQLAlchemy in service)
- JWT token contains ONLY sub/iat/exp (no permission list)
- Password hashing via passlib/bcrypt
"""
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional
from uuid import UUID

from jose import JWTError, jwt
from passlib.context import CryptContext
from services.core.config import settings
from services.core.unit_of_work import UnitOfWork
from services.exceptions.base import ValidationError

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AuthService:
    """Stateless authentication service using Repository pattern."""

    @staticmethod
    def hash_password(password: str) -> str:
        """Hash password using bcrypt."""
        return pwd_context.hash(password)

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify password against hash."""
        return pwd_context.verify(plain_password, hashed_password)

    @staticmethod
    def create_access_token(data: dict, expires_delta=None) -> str:
        """Create JWT token with ONLY sub claim (no permission list)."""
        to_encode = data.copy()
        delta = expires_delta or timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
        expire = datetime.now(tz=timezone.utc) + delta
        to_encode["exp"] = expire
        return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

    @staticmethod
    def create_refresh_token(data: dict) -> str:
        """Create refresh token (separate from access token)."""
        expire = datetime.now(tz=timezone.utc) + timedelta(days=7)
        data["exp"] = expire
        data["type"] = "refresh"
        return jwt.encode(data, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

    @staticmethod
    def verify_token(token: str) -> dict:
        """Decode and validate JWT token."""
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            return payload
        except JWTError:
            raise ValueError("Invalid or expired token")

    async def login(
        self,
        uow: UnitOfWork,
        username: str,
        password: str,
        tenant_code: str,
    ) -> Dict[str, Any]:
        """Authenticate user and return JWT token.

        Flow:
        1. Find tenant by code via TenantRepository
        2. Find user by username via UserRepository
        3. Verify password via bcrypt
        4. Create JWT token with sub only (no permissions in token)
        """
        # Step 1: Find tenant
        from services.identity.repositories.tenant_repository import TenantRepository
        tenant_repo = TenantRepository(uow.session)
        tenant = await tenant_repo.get_by_code(tenant_code)

        if tenant is None or tenant.status != "active":
            raise ValidationError(field="tenant_code", message="Invalid tenant")

        # Step 2: Find user
        from services.identity.repositories.user_repository import UserRepository
        user_repo = UserRepository(uow.session)
        user = await user_repo.get_by_username(username, tenant.id)

        if user is None:
            raise ValidationError(field="username", message="Invalid credentials")

        # Step 3: Verify password
        if not self.verify_password(password, user.password_hash):
            raise ValidationError(field="password", message="Invalid credentials")

        # Step 4: Create JWT token (sub only, no permissions)
        access_token = self.create_access_token({"sub": str(user.id)})
        refresh_token = self.create_refresh_token({"sub": str(user.id)})

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        }

    async def get_user_profile(self, uow: UnitOfWork, user_id: UUID) -> Optional[Dict]:
        """Get user profile via UserRepository."""
        from services.identity.repositories.user_repository import UserRepository
        user_repo = UserRepository(uow.session)
        user = await user_repo.get_by_id(user_id)

        if user is None:
            return None

        return {
            "id": str(user.id),
            "username": user.username,
            "email": user.email,
            "tenant_id": str(user.tenant_id),
            "status": user.status,
        }
