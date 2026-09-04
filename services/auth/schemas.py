"""Auth API Schemas - Pydantic models for authentication endpoints."""
from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    """Login request schema."""
    username: str = Field(..., min_length=1, max_length=128)
    password: str = Field(..., min_length=1)
    tenant_code: str = Field(..., min_length=1, max_length=64)


class TokenResponse(BaseModel):
    """Login response with JWT token."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds
