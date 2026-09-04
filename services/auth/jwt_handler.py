"""JWT Authentication Service - Handles token creation and validation.

Design:
- Tokens contain only 'sub' (user_id), 'iat', 'exp' — no permission list.
- User lookup goes through Repository (not direct SQLAlchemy).
- Password hashing uses bcrypt (matches UserService convention).
"""
from datetime import datetime, timedelta, timezone

from jose import jwt

from services.core.config import settings


class AuthService:
    """Stateless JWT service. User lookup is delegated to repositories."""

    @staticmethod
    def create_access_token(user_id: str) -> str:
        """Create a JWT containing only sub, iat, exp."""
        expire = datetime.now(tz=timezone.utc) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
        payload = {
            "sub": user_id,
            "iat": datetime.now(tz=timezone.utc),
            "exp": expire,
        }
        return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

    @staticmethod
    def create_expired_token(user_id: str) -> str:
        """Create an expired JWT for testing."""
        from jose import jwt
        payload = {
            "sub": user_id,
            "iat": datetime.now(tz=timezone.utc) - timedelta(hours=1),
            "exp": datetime.now(tz=timezone.utc) - timedelta(minutes=30),
        }
        return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

    @staticmethod
    def decode_token(token: str) -> dict:
        """Decode and verify a JWT. Returns payload dict or raises ValueError."""
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            return payload
        except Exception:
            raise ValueError("Invalid or expired token")
