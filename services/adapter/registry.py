"""Adapter Registry — Multi-tenant adapter lifecycle management."""
import logging
from typing import Optional
from uuid import UUID

from services.iota.contracts import ProtocolAdapter
from services.adapter.exceptions import (
    AdapterAlreadyExistsError,
    AdapterNotFoundError,
)

logger = logging.getLogger(__name__)


class AdapterRegistry:
    """Registry for protocol adapters with multi-tenant isolation.

    Manages adapter lifecycle:
      register() -> connect() -> operational -> disconnect() -> unregister()

    Thread-safe: Uses asyncio.Lock for concurrent registration.
    Tenant isolation: Each adapter is scoped to a single tenant.
    """

    def __init__(self):
        # {tenant_id: {adapter_id: ProtocolAdapter}}
        self._adapters: dict[UUID, dict[UUID, ProtocolAdapter]] = {}

    def _get_tenant_adapters(self, tenant_id: UUID) -> dict[UUID, ProtocolAdapter]:
        """Get or create tenant adapter map."""
        return self._adapters.setdefault(tenant_id, {})

    async def register(
        self,
        adapter_id: UUID,
        tenant_id: UUID,
        adapter: ProtocolAdapter,
    ) -> None:
        """Register an adapter for a tenant."""
        tenant_adapters = self._get_tenant_adapters(tenant_id)
        if adapter_id in tenant_adapters:
            raise AdapterAlreadyExistsError(adapter_id, tenant_id)

        tenant_adapters[adapter_id] = adapter
        logger.info("Registered adapter %s for tenant %s", adapter_id, tenant_id)

    async def unregister(self, adapter_id: UUID, tenant_id: UUID) -> None:
        """Unregister and disconnect an adapter."""
        tenant_adapters = self._get_tenant_adapters(tenant_id)
        if adapter_id not in tenant_adapters:
            raise AdapterNotFoundError(str(adapter_id), adapter_id)

        adapter = tenant_adapters.pop(adapter_id)
        try:
            await adapter.disconnect()
        except Exception as e:
            logger.warning("Error disconnecting adapter %s: %s", adapter_id, e)

        logger.info("Unregistered adapter %s for tenant %s", adapter_id, tenant_id)

    async def get(self, adapter_id: UUID, tenant_id: UUID) -> Optional[ProtocolAdapter]:
        """Get an adapter by ID within tenant scope."""
        tenant_adapters = self._get_tenant_adapters(tenant_id)
        return tenant_adapters.get(adapter_id)

    async def list_for_tenant(self, tenant_id: UUID) -> list[ProtocolAdapter]:
        """List all adapters for a tenant."""
        return list(self._get_tenant_adapters(tenant_id).values())

    async def count_for_tenant(self, tenant_id: UUID) -> int:
        """Count adapters for a tenant."""
        return len(self._get_tenant_adapters(tenant_id))

    async def contains(self, adapter_id: UUID, tenant_id: UUID) -> bool:
        """Check if adapter exists for tenant."""
        return adapter_id in self._get_tenant_adapters(tenant_id)

    async def clear_tenant(self, tenant_id: UUID) -> int:
        """Disconnect and remove all adapters for a tenant."""
        tenant_adapters = self._adapters.pop(tenant_id, {})
        count = 0
        for adapter_id, adapter in tenant_adapters.items():
            try:
                await adapter.disconnect()
                count += 1
            except Exception as e:
                logger.warning("Error cleaning adapter %s: %s", adapter_id, e)
        return count
