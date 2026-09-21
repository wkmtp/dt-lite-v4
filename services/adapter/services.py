"""Adapter Service — Orchestration layer for adapter lifecycle and operations."""
import logging
from typing import Optional
from uuid import UUID

from services.iota.contracts import ProtocolAdapter
from services.adapter.exceptions import AdapterNotFoundError, AdapterNotConnectedError
from services.adapter.health import AdapterHealthChecker
from services.adapter.matching import CapabilityAdapterMatcher
from services.adapter.models import CapabilityMatch
from services.adapter.registry import AdapterRegistry
from services.adapter.runtime import AdapterRuntime

logger = logging.getLogger(__name__)


class AdapterService:
    """Orchestrates adapter lifecycle, matching, and operations."""

    def __init__(
        self,
        registry: AdapterRegistry,
        runtime: AdapterRuntime,
        health_checker: AdapterHealthChecker,
        matcher: CapabilityAdapterMatcher,
    ):
        self._registry = registry
        self._runtime = runtime
        self._health_checker = health_checker
        self._matcher = matcher

    async def register_adapter(self, adapter_id: UUID, tenant_id: UUID, adapter: ProtocolAdapter) -> None:
        await self._registry.register(adapter_id, tenant_id, adapter)
        logger.info("Adapter %s registered for tenant %s", adapter_id, tenant_id)

    async def unregister_adapter(self, adapter_id: UUID, tenant_id: UUID) -> None:
        await self._registry.unregister(adapter_id, tenant_id)

    async def get_adapter(self, adapter_id: UUID, tenant_id: UUID) -> Optional[ProtocolAdapter]:
        return await self._registry.get(adapter_id, tenant_id)

    async def list_adapters(self, tenant_id: UUID) -> list[ProtocolAdapter]:
        return await self._registry.list_for_tenant(tenant_id)

    async def connect_adapter(self, adapter_id: UUID, tenant_id: UUID, endpoint: str, credentials_ref: str, config: dict) -> None:
        adapter = await self._registry.get(adapter_id, tenant_id)
        if adapter is None:
            raise AdapterNotFoundError("unknown", adapter_id)
        await self._runtime.connect_with_retry(adapter, endpoint, credentials_ref, config)

    async def disconnect_adapter(self, adapter_id: UUID, tenant_id: UUID) -> None:
        adapter = await self._registry.get(adapter_id, tenant_id)
        if adapter is None:
            raise AdapterNotFoundError("unknown", adapter_id)
        await self._runtime.disconnect_with_cleanup(adapter)

    async def read_data(self, adapter_id: UUID, tenant_id: UUID, external_ids: list[str]):
        adapter = await self._registry.get(adapter_id, tenant_id)
        if adapter is None:
            raise AdapterNotFoundError(str(adapter_id), adapter_id)
        if not await self._runtime.check_health(adapter):
            raise AdapterNotConnectedError(adapter_id)
        return await adapter.read(external_ids)

    async def write_data(self, adapter_id: UUID, tenant_id: UUID, external_id: str, value, data_type: str) -> bool:
        adapter = await self._registry.get(adapter_id, tenant_id)
        if adapter is None:
            raise AdapterNotFoundError(str(adapter_id), adapter_id)
        if not await self._runtime.check_health(adapter):
            raise AdapterNotConnectedError(adapter_id)
        return await adapter.write(external_id, value, data_type)

    async def subscribe_data(self, adapter_id: UUID, tenant_id: UUID, external_id: str, callback) -> str:
        adapter = await self._registry.get(adapter_id, tenant_id)
        if adapter is None:
            raise AdapterNotFoundError(str(adapter_id), adapter_id)
        return await adapter.subscribe(external_id, callback)

    async def unsubscribe_data(self, adapter_id: UUID, tenant_id: UUID, subscription_id: str) -> None:
        adapter = await self._registry.get(adapter_id, tenant_id)
        if adapter is None:
            raise AdapterNotFoundError(str(adapter_id), adapter_id)
        await adapter.unsubscribe(subscription_id)

    async def check_health(self, adapter_id: UUID, tenant_id: UUID) -> dict:
        adapter = await self._registry.get(adapter_id, tenant_id)
        if adapter is None:
            raise AdapterNotFoundError(str(adapter_id), adapter_id)
        status = await self._health_checker.check(
            adapter_id=adapter_id, tenant_id=tenant_id, adapter=adapter,
            adapter_type=str(getattr(adapter, "adapter_id", "unknown")),
            endpoint=getattr(adapter, "_endpoint", "unknown"),
            circuit_state=self._runtime.circuit_state,
        )
        return status.to_dict()

    async def match_capability(self, capability_key: str, data_type: str, unit: Optional[str] = None,
                                semantic_tags: Optional[list[str]] = None,
                                required_capabilities: Optional[list[str]] = None) -> list[CapabilityMatch]:
        return await self._matcher.match(
            capability_key=capability_key, data_type=data_type, unit=unit,
            semantic_tags=semantic_tags, required_capabilities=required_capabilities,
        )

    async def clear_tenant_adapters(self, tenant_id: UUID) -> int:
        return await self._registry.clear_tenant(tenant_id)
