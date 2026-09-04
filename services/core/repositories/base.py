"""Base Repository - Foundation for all domain repositories.

Provides generic CRUD operations using SQLAlchemy 2.x async API.
All repositories inherit from this base class.
"""
import uuid as _uuid_lib
from typing import Any, Generic, Optional, Sequence, Type, TypeVar

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from services.tenant_context import get_tenant_id

T = TypeVar("T")


class BaseRepository(Generic[T]):
    """Generic base repository providing common database operations.

    Design principles:
    - Uses AsyncSession passed in constructor (not created internally)
    - Does NOT call commit() - transaction controlled by Service layer
    - Supports soft delete via deleted_at column
    - Enforces tenant_id filtering where applicable
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, id: Any) -> Optional[T]:
        """Get a single entity by ID."""
        stmt = select(self.model).where(self.model.id == id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list(
        self,
        limit: int = 20,
        offset: int = 0
    ) -> Sequence[T]:
        """List entities with pagination."""
        stmt = select(self.model).offset(offset).limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def count(self) -> int:
        """Count total entities."""
        stmt = select(func.count()).select_from(self.model)
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def create(self, obj: T) -> T:
        """Create a new entity. Caller must commit transaction."""
        self.session.add(obj)
        await self.session.flush()
        await self.session.refresh(obj)
        return obj

    async def update(self, obj: T) -> T:
        """Update an existing entity. Caller must commit transaction."""
        await self.session.merge(obj)
        await self.session.flush()
        return obj

    async def soft_delete(self, id: Any) -> bool:
        """Soft delete an entity by setting deleted_at timestamp.

        Returns True if entity was found and deleted, False otherwise.
        """
        obj = await self.get_by_id(id)
        if obj is None:
            return False

        if hasattr(obj, 'soft_delete'):
            obj.soft_delete()
        else:
            # Fallback for models without soft_delete method
            obj.deleted_at = func.now()

        await self.session.flush()
        return True

    async def hard_delete(self, id: Any) -> bool:
        """Physically delete an entity. Use with caution."""
        obj = await self.get_by_id(id)
        if obj is None:
            return False
        await self.session.delete(obj)
        await self.session.flush()
        return True


class TenantAwareRepository(BaseRepository[T]):
    """Repository that enforces tenant isolation.

    All queries automatically filter by tenant_id when available.
    """

    def __init__(
        self,
        session: AsyncSession,
        model: Type[T],
        tenant_id_column: str = "tenant_id"
    ):
        super().__init__(session)
        self.model = model
        self.tenant_id_column = tenant_id_column

    def _get_tenant_filter(self, tenant_id: Optional[Any] = None) -> Any:
        """Get tenant filter condition."""
        # Use explicit tenant_id if provided
        if tenant_id is not None:
            if isinstance(tenant_id, str):
                tenant_id = _uuid_lib.UUID(tenant_id)
            return getattr(self.model, self.tenant_id_column) == tenant_id

        # Fall back to current tenant context
        ctx_tenant_id = get_tenant_id()
        if ctx_tenant_id:
            return getattr(self.model, self.tenant_id_column) == _uuid_lib.UUID(ctx_tenant_id)

        # No filter - return None (for system-level or admin queries)
        return None

    async def list(
        self,
        tenant_id: Optional[Any] = None,
        limit: int = 20,
        offset: int = 0
    ) -> Sequence[T]:
        """List entities filtered by tenant."""
        stmt = select(self.model)

        # Apply tenant filter if applicable
        tenant_filter = self._get_tenant_filter(tenant_id)
        if tenant_filter is not None:
            stmt = stmt.where(tenant_filter)

        # Exclude soft-deleted records
        if hasattr(self.model, 'deleted_at'):
            stmt = stmt.where(self.model.deleted_at.is_(None))

        stmt = stmt.offset(offset).limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_by_id_for_tenant(
        self,
        entity_id: Any,
        tenant_id: Any
    ) -> Optional[T]:
        """Get entity by ID with explicit tenant verification.

        This method enforces tenant isolation at the repository level.
        Use this instead of base Repository.get_by_id() for tenant-scoped reads.
        """
        stmt = select(self.model).where(
            self.model.id == entity_id,
            getattr(self.model, self.tenant_id_column) == tenant_id,
            self.model.deleted_at.is_(None)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def count(self, tenant_id: Optional[Any] = None) -> int:
        """Count entities filtered by tenant."""
        stmt = select(func.count()).select_from(self.model)

        # Apply tenant filter if applicable
        tenant_filter = self._get_tenant_filter(tenant_id)
        if tenant_filter is not None:
            stmt = stmt.where(tenant_filter)

        # Exclude soft-deleted records
        if hasattr(self.model, 'deleted_at'):
            stmt = stmt.where(self.model.deleted_at.is_(None))

        result = await self.session.execute(stmt)
        return result.scalar_one()
