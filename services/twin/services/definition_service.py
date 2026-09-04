"""DefinitionService — Business logic for TwinDefinition management."""
import logging
from typing import Optional
from uuid import UUID

from services.twin.exceptions import (
    TwinDefinitionNotFoundError,
    TwinDefinitionCodeExistsError,
)
from services.twin.models.definition import TwinDefinition
from services.twin.repositories.definition_repository import DefinitionRepository

logger = logging.getLogger(__name__)


class DefinitionService:
    """Service for managing TwinDefinition entities.

    Responsibilities:
    - Create and validate twin type definitions
    - Manage schema definitions
    - Enforce tenant isolation
    """

    def __init__(self, session) -> None:
        self._repo = DefinitionRepository(session)

    async def create(
        self,
        code: str,
        name: str,
        tenant_id: UUID,
        description: Optional[str] = None,
        schema: Optional[dict] = None,
        metadata: Optional[dict] = None,
    ) -> TwinDefinition:
        """Create a new twin definition.

        Args:
            code: Machine-readable code (unique per tenant).
            name: Human-readable name.
            tenant_id: Current tenant from JWT context.
            description: Optional description.
            schema: JSON schema defining properties.
            metadata: Additional metadata.

        Returns:
            Created TwinDefinition.

        Raises:
            TwinDefinitionCodeExistsError: If code already exists for tenant.
        """
        # Check if code already exists
        existing = await self._repo.get_by_code(code, tenant_id)
        if existing is not None:
            raise TwinDefinitionCodeExistsError(code)

        definition = TwinDefinition(
            tenant_id=tenant_id,
            code=code,
            name=name,
            description=description,
            schema=schema or {},
            meta_data=metadata or {},
        )

        return await self._repo.create(definition)

    async def get(self, definition_id: UUID, tenant_id: UUID) -> TwinDefinition:
        """Get a twin definition by ID.

        Args:
            definition_id: The definition ID.
            tenant_id: Current tenant from JWT context.

        Returns:
            TwinDefinition if found.

        Raises:
            TwinDefinitionNotFoundError: If not found.
        """
        definition = await self._repo.get_by_id_for_tenant(definition_id, tenant_id)
        if definition is None:
            raise TwinDefinitionNotFoundError(definition_id)
        return definition

    async def update(
        self,
        definition_id: UUID,
        tenant_id: UUID,
        name: Optional[str] = None,
        description: Optional[str] = None,
        schema: Optional[dict] = None,
        metadata: Optional[dict] = None,
    ) -> TwinDefinition:
        """Update a twin definition.

        Args:
            definition_id: The definition ID.
            tenant_id: Current tenant from JWT context.
            name: New name.
            description: New description.
            schema: New schema.
            metadata: New metadata.

        Returns:
            Updated TwinDefinition.

        Raises:
            TwinDefinitionNotFoundError: If not found.
        """
        definition = await self._repo.get_by_id_for_tenant(definition_id, tenant_id)
        if definition is None:
            raise TwinDefinitionNotFoundError(definition_id)

        if name is not None:
            definition.name = name
        if description is not None:
            definition.description = description
        if schema is not None:
            definition.schema = schema
        if metadata is not None:
            definition.meta_data = metadata

        return await self._repo.update(definition)

    async def delete(self, definition_id: UUID, tenant_id: UUID) -> bool:
        """Soft delete a twin definition.

        Args:
            definition_id: The definition ID.
            tenant_id: Current tenant from JWT context.

        Returns:
            True if deleted, False if not found.
        """
        return await self._repo.soft_delete(definition_id)

    async def list(
        self,
        tenant_id: UUID,
        limit: int = 100,
        offset: int = 0,
    ) -> list[TwinDefinition]:
        """List twin definitions for a tenant.

        Args:
            tenant_id: Current tenant from JWT context.
            limit: Maximum results.
            offset: Pagination offset.

        Returns:
            List of TwinDefinition objects.
        """
        return await self._repo.list(tenant_id=tenant_id, limit=limit, offset=offset)

    async def count(self, tenant_id: UUID) -> int:
        """Count twin definitions for a tenant.

        Args:
            tenant_id: Current tenant from JWT context.

        Returns:
            Count of definitions.
        """
        return await self._repo.count(tenant_id=tenant_id)
