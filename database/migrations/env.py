"""Alembic configuration for DT-Lite V4.0"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import engine_from_config, pool
from alembic import context
from logging.config import fileConfig

from services.core.models.base import Base as UnifiedBase

# Import all models to register them with the unified Base
# These imports ensure SQLAlchemy knows about both Identity and Core models
import services.identity.models.models  # noqa: F401 - registers Tenant, User, Role, Permission, UserRole, RolePermission
import services.core.models.models      # noqa: F401 - registers Entity, Asset, PropertyDefinition, PropertyValue, Relationship

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Override the URL to use synchronous driver (alembic runs synchronously)
if config.config_ini_section:
    section = config.get_section(config.config_ini_section)
    url = section.get('sqlalchemy.url')
    if url and 'asyncpg' in url:
        # Replace asyncpg with psycopg2 for synchronous operations
        section['sqlalchemy.url'] = url.replace('postgresql+asyncpg://', 'postgresql://')

# Unified metadata from single Base
target_metadata = UnifiedBase.metadata

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )
        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
