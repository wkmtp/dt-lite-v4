"""Adapter Registry - In-Memory Adapter Lookup.

The registry manages adapter registration/unregistration and provides
lookup by name. It does NOT handle:
- Tenant authorization
- Database persistence
- Business logic

Registry is intentionally stateless regarding tenant context.
Tenant isolation happens at the Service layer.
"""
from typing import Any

from services.adapter.exceptions import AdapterNotFoundError


class AdapterRegistry:
    """In-memory registry for ProtocolAdapter instances.

    Usage:
        registry = AdapterRegistry()
        registry.register("simulator", SimulatorAdapter())
        adapter = registry.get("simulator")
        registry.remove("simulator")
    """

    def __init__(self) -> None:
        self._adapters: dict[str, Any] = {}

    def register(self, name: str, adapter: Any) -> None:
        """Register an adapter instance.

        Args:
            name: Unique adapter name (e.g., "simulator", "test-adapter").
            adapter: ProtocolAdapter implementing instance.

        Raises:
            ValueError: If adapter is not a ProtocolAdapter subclass.
        """
        from services.iota.contracts import ProtocolAdapter
        if not isinstance(adapter, ProtocolAdapter):
            raise ValueError(
                f"Adapter '{name}' must implement ProtocolAdapter interface"
            )
        self._adapters[name] = adapter

    def get(self, name: str) -> Any:
        """Get registered adapter by name.

        Args:
            name: Adapter name.

        Returns:
            ProtocolAdapter instance.

        Raises:
            AdapterNotFoundError: If adapter is not registered.
        """
        adapter = self._adapters.get(name)
        if adapter is None:
            raise AdapterNotFoundError(name)
        return adapter

    def remove(self, name: str) -> None:
        """Remove adapter from registry.

        Args:
            name: Adapter name to remove.

        Raises:
            AdapterNotFoundError: If adapter is not registered.
        """
        if name not in self._adapters:
            raise AdapterNotFoundError(name)
        del self._adapters[name]

    def list_adapters(self) -> list[str]:
        """List all registered adapter names.

        Returns:
            List of adapter names.
        """
        return list(self._adapters.keys())

    def contains(self, name: str) -> bool:
        """Check if adapter is registered.

        Args:
            name: Adapter name.

        Returns:
            True if registered, False otherwise.
        """
        return name in self._adapters

    def clear(self) -> None:
        """Remove all adapters from registry."""
        self._adapters.clear()

    @property
    def count(self) -> int:
        """Number of registered adapters."""
        return len(self._adapters)
