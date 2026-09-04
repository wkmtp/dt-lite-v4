"""Twin services — Integration layer combining registry, state, and binding.

This module provides the main service interface for the Twin Runtime.
It coordinates between TwinEntityRegistry, TwinStateManager, and EntityBindingService.
"""
import logging
from typing import Optional
from uuid import UUID

from services.iota.contracts import NormalizedTelemetry
from services.iota.repositories.device_repository import DeviceRepository
from services.twin.binding import EntityBindingService
from services.twin.models import TwinEntity
from services.twin.registry import TwinEntityRegistry
from services.twin.state import TwinStateManager

logger = logging.getLogger(__name__)


class TwinService:
    """Main service for Twin Runtime operations.

    This service coordinates between registry, state manager, and binding service
    to provide a unified interface for twin entity management.
    """

    def __init__(self, session=None) -> None:
        """Initialize twin service.

        Args:
            session: Database session (optional, not used directly).
        """
        self._registry = TwinEntityRegistry()
        self._state_manager = TwinStateManager(self._registry)
        # Note: DeviceRepository requires session, created on demand
        self._session = session

    def _get_device_repo(self) -> DeviceRepository:
        """Get or create DeviceRepository instance.

        Returns:
            DeviceRepository instance.
        """
        if self._session:
            return DeviceRepository(self._session)
        # Fallback: create without session for testing
        from unittest.mock import MagicMock
        mock_session = MagicMock()
        return DeviceRepository(mock_session)

    # ==================== Entity Management ====================

    def register_entity(
        self,
        name: str,
        entity_type: str,
        tenant_id: UUID,
        device_id: Optional[UUID] = None,
        template: Optional[dict] = None,
    ) -> TwinEntity:
        """Register a new TwinEntity.

        Args:
            name: Human-readable name.
            entity_type: Category type (e.g., "pump", "valve").
            tenant_id: Current tenant from JWT context.
            device_id: Optional linked device ID.
            template: Optional template configuration.

        Returns:
            Registered TwinEntity.
        """
        entity = TwinEntity(
            tenant_id=tenant_id,
            name=name,
            entity_type=entity_type,
            device_id=device_id,
            template=template or {},
        )
        return self._registry.register(entity)

    def get_entity(self, entity_id: UUID, tenant_id: UUID) -> Optional[TwinEntity]:
        """Get a TwinEntity by ID.

        Args:
            entity_id: The entity ID.
            tenant_id: Current tenant from JWT context.

        Returns:
            TwinEntity if found, None otherwise.
        """
        return self._registry.get(entity_id, tenant_id)

    def remove_entity(self, entity_id: UUID, tenant_id: UUID) -> bool:
        """Remove a TwinEntity.

        Args:
            entity_id: The entity ID.
            tenant_id: Current tenant from JWT context.

        Returns:
            True if removed, False if not found.
        """
        return self._registry.remove(entity_id, tenant_id)

    def list_entities(self, tenant_id: UUID, limit: int = 100, offset: int = 0) -> list[TwinEntity]:
        """List TwinEntities for a tenant.

        Args:
            tenant_id: Current tenant from JWT context.
            limit: Maximum number of entities.
            offset: Pagination offset.

        Returns:
            List of TwinEntity objects.
        """
        return self._registry.list(tenant_id, limit=limit, offset=offset)

    def count_entities(self, tenant_id: UUID) -> int:
        """Count TwinEntities for a tenant.

        Args:
            tenant_id: Current tenant from JWT context.

        Returns:
            Number of entities.
        """
        return self._registry.count(tenant_id)

    # ==================== State Management ====================

    def update_state(
        self,
        entity_id: UUID,
        telemetry: NormalizedTelemetry,
        tenant_id: UUID,
    ) -> dict:
        """Update entity state from telemetry.

        Args:
            entity_id: The target entity ID.
            telemetry: NormalizedTelemetry event.
            tenant_id: Current tenant from JWT context.

        Returns:
            Updated state dictionary.
        """
        return self._state_manager.update_state(entity_id, telemetry, tenant_id)

    def get_state(self, entity_id: UUID, tenant_id: UUID) -> Optional[dict]:
        """Get current state of an entity.

        Args:
            entity_id: The entity ID.
            tenant_id: Current tenant from JWT context.

        Returns:
            State dictionary or None.
        """
        return self._state_manager.get_state(entity_id, tenant_id)

    def clear_state(self, entity_id: UUID, tenant_id: UUID) -> bool:
        """Clear state of an entity.

        Args:
            entity_id: The entity ID.
            tenant_id: Current tenant from JWT context.

        Returns:
            True if cleared, False if not found.
        """
        return self._state_manager.clear_state(entity_id, tenant_id)

    def list_states(self, tenant_id: UUID, limit: int = 100, offset: int = 0) -> list:
        """List all entity states for a tenant.

        Args:
            tenant_id: Current tenant from JWT context.
            limit: Maximum number.
            offset: Pagination offset.

        Returns:
            List of state dictionaries.
        """
        return self._state_manager.list_states(tenant_id, limit=limit, offset=offset)

    # ==================== Binding Management ====================

    def create_binding(
        self,
        device_id: UUID,
        entity_id: UUID,
        tenant_id: UUID,
        binding_type: str = "default",
    ):
        """Create a binding between device and entity.

        Args:
            device_id: Physical device ID.
            entity_id: Twin entity ID.
            tenant_id: Current tenant from JWT context.
            binding_type: Type of binding.

        Returns:
            Created binding record.
        """
        device_repo = self._get_device_repo()
        binding_service = EntityBindingService(self._registry, device_repo)
        return binding_service.create_binding(device_id, entity_id, tenant_id, binding_type)

    def get_binding(self, binding_id: UUID, tenant_id: UUID):
        """Get a binding by ID.

        Args:
            binding_id: The binding ID.
            tenant_id: Current tenant from JWT context.

        Returns:
            Binding record or None.
        """
        device_repo = self._get_device_repo()
        binding_service = EntityBindingService(self._registry, device_repo)
        return binding_service.get_binding(binding_id, tenant_id)

    def remove_binding(self, binding_id: UUID, tenant_id: UUID) -> bool:
        """Remove a binding.

        Args:
            binding_id: The binding ID.
            tenant_id: Current tenant from JWT context.

        Returns:
            True if removed, False otherwise.
        """
        device_repo = self._get_device_repo()
        binding_service = EntityBindingService(self._registry, device_repo)
        return binding_service.remove_binding(binding_id, tenant_id)

    def list_bindings(self, tenant_id: UUID, limit: int = 100, offset: int = 0):
        """List bindings for a tenant.

        Args:
            tenant_id: Current tenant from JWT context.
            limit: Maximum number.
            offset: Pagination offset.

        Returns:
            List of binding records.
        """
        device_repo = self._get_device_repo()
        binding_service = EntityBindingService(self._registry, device_repo)
        return binding_service.list_bindings(tenant_id, limit=limit, offset=offset)
