"""Adapter Runtime - Lifecycle Coordination Layer.

The runtime manages adapter instances through their lifecycle:
  create → connect → start → running → stop → disconnect

It does NOT handle:
- Data persistence (IOTA services do that)
- Tenant authorization (Service layer does that)
- Protocol-specific logic (each adapter implements that)

The runtime coordinates between the registry, lifecycle state machine,
and health monitor to provide a unified interface for adapter management.
"""
import logging
from typing import Any, Optional

from services.adapter.exceptions import (
    AdapterCapabilityError,
    AdapterNotFoundError,
)
from services.adapter.health import HealthMonitor
from services.adapter.lifecycle import AdapterLifecycle
from services.adapter.models import AdapterInstance
from services.iota.contracts import AdapterCapability, DiscoveryResult, NormalizedTelemetry

logger = logging.getLogger(__name__)


class AdapterRuntime:
    """Coordinates adapter lifecycle, health, and discovery operations.

    This class is the primary interface for managing adapter instances
    at runtime. It maintains AdapterInstance metadata and enforces
    lifecycle state transitions.
    """

    def __init__(self, registry: Any):
        """Initialize runtime with adapter registry.

        Args:
            registry: AdapterRegistry instance.
        """
        self._registry = registry
        self._instances: dict[str, AdapterInstance] = {}
        self._lifecycles: dict[str, AdapterLifecycle] = {}
        self._health_monitor = HealthMonitor()

    @property
    def health_monitor(self) -> HealthMonitor:
        return self._health_monitor

    async def create(self, name: str, config: Optional[dict] = None) -> None:
        """Create (initialize) an adapter instance.

        Args:
            name: Registered adapter name.
            config: Optional initialization configuration.

        Raises:
            AdapterNotFoundError: If adapter not in registry.
        """
        if name not in self._registry.list_adapters():
            raise AdapterNotFoundError(name)

        adapter = self._registry.get(name)
        instance = AdapterInstance(name=name, adapter=adapter)
        self._instances[name] = instance
        logger.info("Adapter '%s' created", name)

    async def connect(self, name: str, endpoint: str, credentials_ref: str,
                      config: Optional[dict] = None) -> None:
        """Connect adapter to endpoint.

        Transition: CREATED -> CONNECTED

        Args:
            name: Adapter instance name.
            endpoint: Connection endpoint URL.
            credentials_ref: Reference to secrets in SecretProvider.
            config: Additional connection configuration.
        """
        instance = self._get_instance(name)
        if name not in self._lifecycles:
            self._lifecycles[name] = AdapterLifecycle(name)
        lifecycle = self._lifecycles[name]

        await lifecycle.connect(instance.adapter, endpoint, credentials_ref, config or {})
        instance.update_state(lifecycle.state.value)
        instance.connected_endpoint = endpoint
        logger.info("Adapter '%s' connected to %s", name, "[ENDPOINT_REDACTED]")

    async def start(self, name: str) -> None:
        """Start adapter operation.

        Transition: CONNECTED -> RUNNING

        Args:
            name: Adapter instance name.
        """
        instance = self._get_instance(name)
        lifecycle = self._lifecycles.get(name)
        if lifecycle is None:
            lifecycle = AdapterLifecycle(name)
            self._lifecycles[name] = lifecycle

        await lifecycle.start(instance.adapter)
        instance.update_state(lifecycle.state.value)
        logger.info("Adapter '%s' started", name)

    async def stop(self, name: str) -> None:
        """Stop adapter operation.

        Transition: RUNNING -> STOPPED

        Args:
            name: Adapter instance name.
        """
        instance = self._get_instance(name)
        lifecycle = self._lifecycles.get(name)
        if lifecycle is None:
            lifecycle = AdapterLifecycle(name)
            self._lifecycles[name] = lifecycle

        await lifecycle.stop(instance.adapter)
        instance.update_state(lifecycle.state.value)
        instance.connected_endpoint = None
        logger.info("Adapter '%s' stopped", name)

    async def disconnect(self, name: str) -> None:
        """Disconnect adapter.

        Args:
            name: Adapter instance name.
        """
        instance = self._get_instance(name)
        lifecycle = self._lifecycles.get(name)
        if lifecycle is None:
            lifecycle = AdapterLifecycle(name)
            self._lifecycles[name] = lifecycle

        try:
            await lifecycle.reset(instance.adapter)
        except Exception as e:
            logger.warning("Adapter '%s' disconnect error (best-effort cleanup): %s",
                          name, e)
            lifecycle.mark_failed("")

        instance.update_state(lifecycle.state.value)
        instance.connected_endpoint = None
        logger.info("Adapter '%s' disconnected", name)

    async def destroy(self, name: str) -> None:
        """Destroy adapter instance (remove from runtime tracking).

        Args:
            name: Adapter instance name.
        """
        instance = self._get_instance(name)

        if instance.state != "CREATED":
            try:
                await self.disconnect(name)
            except Exception:
                pass  # Best effort cleanup

        del self._instances[name]
        self._health_monitor.clear_cache()
        logger.info("Adapter '%s' destroyed", name)

    async def discover(self, name: str) -> list[DiscoveryResult]:
        """Discover devices/data points via adapter.

        Args:
            name: Adapter instance name.

        Returns:
            List of DiscoveryResult.
        """
        instance = self._validate_capability(name, AdapterCapability.DISCOVERY)
        return await instance.adapter.discover()

    async def read(self, name: str, external_ids: list[str]) -> list[NormalizedTelemetry]:
        """Read telemetry values from adapter.

        Args:
            name: Adapter instance name.
            external_ids: List of data point external IDs.

        Returns:
            List of NormalizedTelemetry.
        """
        instance = self._validate_capability(name, AdapterCapability.READ)
        return await instance.adapter.read(external_ids)

    async def write(self, name: str, external_id: str, value: Any,
                    data_type: str) -> bool:
        """Write value to adapter data point.

        Args:
            name: Adapter instance name.
            external_id: Target data point external ID.
            value: Value to write.
            data_type: Data type string.

        Returns:
            True if write succeeded.
        """
        instance = self._validate_capability(name, AdapterCapability.WRITE)
        return await instance.adapter.write(external_id, value, data_type)

    async def subscribe(self, name: str, external_id: str,
                        callback: Any) -> str:
        """Subscribe to adapter data point.

        Args:
            name: Adapter instance name.
            external_id: Data point external ID.
            callback: Async callback function.

        Returns:
            Subscription ID.
        """
        instance = self._validate_capability(name, AdapterCapability.SUBSCRIBE)
        return await instance.adapter.subscribe(external_id, callback)

    async def unsubscribe(self, name: str, subscription_id: str) -> None:
        """Unsubscribe from adapter data point.

        Args:
            name: Adapter instance name.
            subscription_id: Subscription ID to cancel.
        """
        instance = self._get_instance(name)
        await instance.adapter.unsubscribe(subscription_id)

    async def health_check(self, name: str) -> dict:
        """Perform health check on adapter instance.

        Args:
            name: Adapter instance name.

        Returns:
            Health report dict.
        """
        instance = self._get_instance(name)
        health = await self._health_monitor.check(name, instance.adapter)
        instance.record_health(health.status, health.message, health.metadata)

        if health.status == "ERROR":
            instance.record_error(health.message)

        return health.to_dict()

    def get_status(self, name: str) -> dict:
        """Get runtime status for adapter instance.

        Args:
            name: Adapter instance name.

        Returns:
            Status dict with state, health, etc.
        """
        instance = self._get_instance(name)
        return {
            "name": name,
            "state": instance.state,
            "health_status": instance.health_status,
            "last_check_time": instance.last_health_check.isoformat() if instance.last_health_check else None,
            "error_count": instance.error_count,
            "last_error": instance.last_error,
        }

    def list_instances(self) -> list[str]:
        """List all active adapter instance names.

        Returns:
            List of instance names.
        """
        return list(self._instances.keys())

    def _get_instance(self, name: str) -> AdapterInstance:
        """Get adapter instance or raise error."""
        instance = self._instances.get(name)
        if instance is None:
            raise AdapterNotFoundError(name)
        return instance

    def _validate_capability(self, name: str, capability: AdapterCapability) -> AdapterInstance:
        """Validate adapter has required capability.

        Args:
            name: Adapter instance name.
            capability: Required capability.

        Returns:
            AdapterInstance.

        Raises:
            AdapterCapabilityError: If capability not supported.
        """
        instance = self._get_instance(name)
        supported = instance.adapter.capabilities()
        if capability not in supported:
            raise AdapterCapabilityError(name, capability.value)
        return instance
