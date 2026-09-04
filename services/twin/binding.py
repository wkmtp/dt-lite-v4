"""EntityBindingService — Manages Device ↔ TwinEntity relationships.

This service creates and maintains binding relationships between
physical devices (Task 5) and digital twin entities (Task 8).

Rules:
  - Must verify tenant ownership for both sides
  - Auto-create Device or DataPoint is FORBIDDEN
  - Binding is a runtime relationship, not a database persistence
"""
import logging
from typing import Optional
from uuid import UUID

from services.iota.repositories.device_repository import DeviceRepository
from services.twin.exceptions import (
    TwinBindingError,
    TwinEntityNotFoundError,
)
from services.twin.registry import TwinEntityRegistry

logger = logging.getLogger(__name__)


class BindingRecord:
    """In-memory binding relationship between Device and TwinEntity."""

    def __init__(
        self,
        id: UUID,
        device_id: UUID,
        entity_id: UUID,
        tenant_id: UUID,
        binding_type: str = "default",
    ) -> None:
        self.id = id
        self.device_id = device_id
        self.entity_id = entity_id
        self.tenant_id = tenant_id
        self.binding_type = binding_type

    def __repr__(self) -> str:
        return (
            f"<BindingRecord(id={self.id}, device={self.device_id}, "
            f"entity={self.entity_id}, type={self.binding_type})>"
        )


class EntityBindingService:
    """Manages Device ↔ TwinEntity binding relationships.

    This service operates entirely in memory (no database writes).
    All operations require tenant verification.
    """

    def __init__(
        self,
        registry: TwinEntityRegistry,
        device_repo: DeviceRepository,
    ) -> None:
        """Initialize with registry and device repository.

        Args:
            registry: The shared twin entity registry.
            device_repo: DeviceRepository for tenant ownership verification.
        """
        self._registry = registry
        self._device_repo = device_repo
        # In-memory bindings: {tenant_id: {binding_id: BindingRecord}}
        self._bindings: dict[UUID, dict[UUID, BindingRecord]] = {}

    def create_binding(
        self,
        device_id: UUID,
        entity_id: UUID,
        tenant_id: UUID,
        binding_type: str = "default",
    ) -> BindingRecord:
        """Create a binding between a Device and a TwinEntity.

        Args:
            device_id: The physical device ID.
            entity_id: The twin entity ID.
            tenant_id: Current tenant from JWT context.
            binding_type: Type of binding (default, mirror, aggregate).

        Returns:
            Created BindingRecord.

        Raises:
            TwinBindingError: If validation fails.
            TwinEntityNotFoundError: If entity doesn't exist for tenant.
            TwinTenantMismatchError: If device or entity doesn't belong to tenant.
        """
        # Verify device exists and belongs to tenant
        device = self._device_repo.get_by_id_for_tenant(device_id, tenant_id)
        if device is None:
            raise TwinBindingError(
                f"Device {device_id} not found or does not belong to tenant {tenant_id}",
                code="DEVICE_NOT_FOUND",
            )

        # Verify entity exists and belongs to tenant
        entity = self._registry.get(entity_id, tenant_id)
        if entity is None:
            raise TwinEntityNotFoundError(entity_id)

        # Create binding
        from uuid import uuid4
        binding_id = uuid4()
        binding = BindingRecord(
            id=binding_id,
            device_id=device_id,
            entity_id=entity_id,
            tenant_id=tenant_id,
            binding_type=binding_type,
        )

        tenant_bindings = self._bindings.setdefault(tenant_id, {})
        tenant_bindings[binding_id] = binding

        logger.info(
            "Created binding: device=%s entity=%s type=%s tenant=%s",
            device_id,
            entity_id,
            binding_type,
            tenant_id,
        )

        return binding

    def get_binding(self, binding_id: UUID, tenant_id: UUID) -> Optional[BindingRecord]:
        """Get a binding by ID.

        Args:
            binding_id: The binding ID.
            tenant_id: Current tenant from JWT context.

        Returns:
            BindingRecord if found, None otherwise.
        """
        tenant_bindings = self._bindings.get(tenant_id, {})
        return tenant_bindings.get(binding_id)

    def get_binding_by_device(self, device_id: UUID, tenant_id: UUID) -> Optional[BindingRecord]:
        """Get binding for a specific device.

        Args:
            device_id: The device ID.
            tenant_id: Current tenant from JWT context.

        Returns:
            BindingRecord if found, None otherwise.
        """
        tenant_bindings = self._bindings.get(tenant_id, {})
        for binding in tenant_bindings.values():
            if binding.device_id == device_id:
                return binding
        return None

    def remove_binding(self, binding_id: UUID, tenant_id: UUID) -> bool:
        """Remove a binding.

        Args:
            binding_id: The binding ID.
            tenant_id: Current tenant from JWT context.

        Returns:
            True if removed, False if not found.
        """
        tenant_bindings = self._bindings.get(tenant_id, {})
        if binding_id in tenant_bindings:
            del tenant_bindings[binding_id]
            logger.info("Removed binding: id=%s tenant=%s", binding_id, tenant_id)
            return True
        return False

    def list_bindings(self, tenant_id: UUID, limit: int = 100, offset: int = 0) -> list[BindingRecord]:
        """List all bindings for a tenant.

        Args:
            tenant_id: Current tenant from JWT context.
            limit: Maximum number of bindings.
            offset: Pagination offset.

        Returns:
            List of BindingRecord objects.
        """
        tenant_bindings = self._bindings.get(tenant_id, {})
        bindings = list(tenant_bindings.values())
        return bindings[offset: offset + limit]

    def count_bindings(self, tenant_id: UUID) -> int:
        """Count bindings for a tenant.

        Args:
            tenant_id: Current tenant from JWT context.

        Returns:
            Number of bindings.
        """
        return len(self._bindings.get(tenant_id, {}))
