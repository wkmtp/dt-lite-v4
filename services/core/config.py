"""Configuration for DT-Lite services using Pydantic Settings"""
from pydantic_settings import BaseSettings
from typing import Optional, List


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://dtlite_user:dtlite_pass@localhost:5432/dtlite"
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # JWT Auth
    SECRET_KEY: str = "dev-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Application
    APP_NAME: str = "DT-Lite"
    APP_VERSION: str = "4.0.0"
    DEBUG: bool = True
    
    # CORS
    BACKEND_CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:5173"]
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
