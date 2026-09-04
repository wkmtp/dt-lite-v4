"""Database engine configuration"""
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool
import os

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://dtlite_user:dtlite_pass@localhost:5432/dtlite"
)

engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    poolclass=StaticPool if "test" in DATABASE_URL else None,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db():
    """Get database session dependency for FastAPI"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db():
    """Initialize database tables"""
    from services.core.models import Base
    from services.identity.models import Tenant, User, Role, Permission
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
