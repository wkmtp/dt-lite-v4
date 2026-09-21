"""Tool Registry with hot-reload support.

Loads tool definitions from ``services/ai/tools/*.py`` on demand and
supports live reload so that new tools are picked up without a restart.
Each tool is scoped to a ``tenant_id`` for isolation.
"""
from __future__ import annotations

import importlib
import inspect
import logging
import pkgutil
from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel, Field

from services.ai.config import AIConfig, get_ai_config

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class ToolDescriptor(BaseModel):
    """Metadata about a registered tool."""

    tool_name: str = Field(..., description="Unique tool identifier")
    description: str = Field(..., description="Tool description exposed to the LLM")
    module_path: str = Field(..., description="Python module path of the tool class")
    class_name: str = Field(..., description="Name of the tool class")
    is_async: bool = Field(default=False, description="Whether the execute method is async")
    input_schema: dict[str, Any] = Field(
        default_factory=dict,
        description="JSON Schema of the tool's input parameters",
    )


# ---------------------------------------------------------------------------
# ToolRegistry
# ---------------------------------------------------------------------------

class ToolRegistry:
    """Registry that discovers and loads agent tools from the tools directory.

    Tool classes must implement::

        async def execute(self, tenant_id: str, **kwargs: Any) -> Any

    or::

        def execute(self, tenant_id: str, **kwargs: Any) -> Any

    The registry caches instances per-tenant and supports hot reload
    by clearing the cache and re-importing when ``reload()`` is called.
    """

    def __init__(
        self,
        config: Optional[AIConfig] = None,
        tools_dir: Optional[Path] = None,
    ) -> None:
        self.config = config or get_ai_config()
        self._tools_dir = tools_dir or self.config.AGENT_TOOL_REGISTRY_DIR
        self._descriptors: dict[str, ToolDescriptor] = {}
        self._instances: dict[str, Any] = {}
        self._load_all()

    # ------------------------------------------------------------------
    # Discovery
    # ------------------------------------------------------------------

    def _load_all(self) -> None:
        """Scan the tools directory and import every tool module."""
        tools_path = Path(__file__).parent / ".." / ".." / ".." / "tools"
        tools_path = tools_path.resolve()

        if not tools_path.exists():
            logger.warning("Tools directory not found: %s", tools_path)
            return

        for module_info in pkgutil.iter_modules([str(tools_path)]):
            if module_info.name.startswith("_"):
                continue
            try:
                module = importlib.import_module(
                    f"services.ai.agent.tools.{module_info.name}"
                )
                self._discover_tools_from_module(module, module_info.name)
            except Exception as exc:
                logger.warning(
                    "Failed to load tool module %s: %s",
                    module_info.name,
                    exc,
                    exc_info=True,
                )

    def _discover_tools_from_module(
        self,
        module: Any,
        module_name: str,
    ) -> None:
        """Inspect a module for tool classes and register them."""
        for name, obj in inspect.getmembers(module, inspect.isclass):
            if not hasattr(obj, "execute"):
                continue
            if not (hasattr(obj, "tool_name") or hasattr(obj, "TOOL_NAME")):
                continue

            tool_name = getattr(obj, "tool_name") or getattr(obj, "TOOL_NAME", name.lower())
            is_async = asyncio.iscoroutinefunction(obj.execute) or asyncio.iscoroutinefunction(
                getattr(obj, "execute", None)
            )

            # Try to extract input schema from class docstring or execute signature
            input_schema: dict[str, Any] = {}
            execute_sig = inspect.signature(obj.execute)
            for pname, param in execute_sig.parameters.items():
                if pname in ("self", "tenant_id"):
                    continue
                input_schema[pname] = {
                    "type": self._type_to_json_schema(param.annotation),
                    "description": param.default if param.default is not inspect.Parameter.empty else "",
                }

            self._descriptors[tool_name] = ToolDescriptor(
                tool_name=tool_name,
                description=getattr(obj, "description", f"Tool: {name}"),
                module_path=f"services.ai.agent.tools.{module_name}",
                class_name=name,
                is_async=is_async,
                input_schema=input_schema,
            )
            logger.info("Registered tool: %s (async=%s)", tool_name, is_async)

    @staticmethod
    def _type_to_json_schema(annotation: Any) -> str:
        """Best-effort mapping of Python type hints to JSON Schema type strings."""
        if annotation is str:
            return "string"
        if annotation is int:
            return "integer"
        if annotation is float:
            return "number"
        if annotation is bool:
            return "boolean"
        if annotation is list:
            return "array"
        if annotation is dict:
            return "object"
        return "string"  # fallback

    # ------------------------------------------------------------------
    # Lookup & instantiation
    # ------------------------------------------------------------------

    def get_descriptor(self, tool_name: str) -> Optional[ToolDescriptor]:
        """Return the descriptor for *tool_name*, or None if unknown."""
        return self._descriptors.get(tool_name)

    def list_tools(self) -> list[ToolDescriptor]:
        """Return all registered tool descriptors."""
        return list(self._descriptors.values())

    def get_instance(
        self,
        tool_name: str,
        tenant_id: str,
    ) -> Optional[Any]:
        """Return (or create) a tool instance scoped to *tenant_id*."""
        descriptor = self._descriptors.get(tool_name)
        if descriptor is None:
            return None

        cache_key = f"{tool_name}:{tenant_id}"
        if cache_key not in self._instances:
            try:
                module = importlib.import_module(descriptor.module_path)
                cls = getattr(module, descriptor.class_name)
                self._instances[cache_key] = cls(tenant_id=tenant_id)
            except Exception as exc:
                logger.error("Failed to instantiate tool %s: %s", tool_name, exc, exc_info=True)
                return None
        return self._instances[cache_key]

    # ------------------------------------------------------------------
    # Hot reload
    # ------------------------------------------------------------------

    def reload(self) -> int:
        """Clear the instance cache and re-scan for new tools.

        Returns:
            Number of tools currently registered after reload.
        """
        self._instances.clear()
        self._descriptors.clear()
        self._load_all()
        logger.info("Tool registry reloaded: %d tools registered", len(self._descriptors))
        return len(self._descriptors)
