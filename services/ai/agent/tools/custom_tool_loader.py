"""Custom Tool Loader — dynamic loading and hot-reload of agent tools.

Scans the services/ai/tools/custom/ directory for tool modules,
validates their schemas, and supports live reload without restarting
the agent runtime.

Tool modules must follow the约定::
  - Contain a class with `tool_name`, `description`, and `execute` method
  - Use async/await for execute
  - Accept tenant_id as first parameter
"""
from __future__ import annotations

import importlib
import inspect
import logging
import pkgutil
from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel, Field, ValidationError

from services.ai.config import AIConfig, get_ai_config

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class ToolSchema(BaseModel):
    """Schema metadata for a tool."""
    tool_name: str = Field(..., description="Unique tool identifier")
    description: str = Field(..., description="Tool description for LLM")
    input_schema: dict[str, Any] = Field(
        default_factory=dict,
        description="JSON Schema describing tool inputs",
    )
    output_schema: Optional[dict[str, Any]] = Field(
        None,
        description="JSON Schema describing tool outputs",
    )
    is_async: bool = Field(default=True, description="Whether execute is async")
    module_path: str = Field(..., description="Python module path")
    class_name: str = Field(..., description="Tool class name")
    version: str = Field("1.0.0", description="Tool version")
    author: Optional[str] = Field(None, description="Tool author")
    tags: list[str] = Field(default_factory=list, description="Tool tags")


class ToolValidationError(BaseModel):
    """Validation error for a tool schema."""
    tool_name: str
    errors: list[str] = Field(default_factory=list)
    is_valid: bool = False


class ToolLoadResult(BaseModel):
    """Result of loading a tool."""
    success: bool = Field(True, description="Whether loading succeeded")
    schema: Optional[ToolSchema] = Field(None, description="Tool schema if valid")
    errors: list[str] = Field(default_factory=list, description="Validation errors")
    module_path: str = Field(..., description="Module path that was loaded")


# ---------------------------------------------------------------------------
# CustomToolLoader
# ---------------------------------------------------------------------------

class CustomToolLoader:
    """Dynamically loads and validates agent tools from a directory.

    Scans ``services/ai/tools/custom/`` for Python modules containing
    tool classes. Supports hot-reload and schema validation.

    Example tool module structure::

        # services/ai/tools/custom/my_tool.py
        from services.ai.agent.tools.base import BaseTool

        class MyCustomTool(BaseTool):
            tool_name = "my_custom_tool"
            description = "My custom tool description"

            async def execute(self, tenant_id: str, param1: str, **kwargs):
                # Tool implementation
                return {"result": param1}
    """

    def __init__(
        self,
        tenant_id: str,
        config: Optional[AIConfig] = None,
        tools_dir: Optional[Path] = None,
    ) -> None:
        self.tenant_id = tenant_id
        self.config = config or get_ai_config()
        self._tools_dir = tools_dir or Path(__file__).parent.parent.parent / "tools" / "custom"
        self._loaded_tools: dict[str, ToolSchema] = {}
        self._tool_classes: dict[str, type] = {}
        self._tool_instances: dict[str, Any] = {}
        self._module_cache: dict[str, Any] = {}
        self._last_scan_time: float = 0

        # Scan and load tools on initialization
        self.scan()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def scan(self) -> list[ToolLoadResult]:
        """Scan the tools directory and load all valid tool modules.

        Returns:
            List of ToolLoadResult for each module scanned.
        """
        results: list[ToolLoadResult] = []

        if not self._tools_dir.exists():
            logger.warning("Custom tools directory not found: %s", self._tools_dir)
            return results

        # Clear previous scans
        self._loaded_tools.clear()
        self._tool_classes.clear()
        self._tool_instances.clear()

        for module_info in pkgutil.iter_modules([str(self._tools_dir)]):
            if module_info.name.startswith("_"):
                continue

            module_path = f"services.ai.tools.custom.{module_info.name}"
            result = self._load_module(module_path, module_info.name)
            results.append(result)

        self._last_scan_time = self._get_current_time()
        logger.info(
            "Scanned %d modules, loaded %d tools",
            len(results),
            len(self._loaded_tools),
        )
        return results

    def reload(self) -> list[ToolLoadResult]:
        """Force reload all tools (clear cache and re-scan).

        Returns:
            List of ToolLoadResult for each module reloaded.
        """
        self._module_cache.clear()
        return self.scan()

    def get_tool(self, tool_name: str) -> Optional[ToolSchema]:
        """Get a tool schema by name.

        Args:
            tool_name: Tool identifier.

        Returns:
            ToolSchema if found, None otherwise.
        """
        return self._loaded_tools.get(tool_name)

    def get_tool_instance(
        self,
        tool_name: str,
        tenant_id: Optional[str] = None,
    ) -> Optional[Any]:
        """Get a tool instance by name.

        Args:
            tool_name: Tool identifier.
            tenant_id: Optional tenant ID (defaults to self.tenant_id).

        Returns:
            Tool instance if found, None otherwise.
        """
        cache_key = f"{tool_name}:{tenant_id or self.tenant_id}"
        if cache_key not in self._tool_instances:
            schema = self._loaded_tools.get(tool_name)
            if schema:
                instance = self._instantiate_tool(schema, tenant_id or self.tenant_id)
                self._tool_instances[cache_key] = instance

        return self._tool_instances.get(cache_key)

    def list_tools(self) -> list[ToolSchema]:
        """List all loaded tool schemas.

        Returns:
            List of ToolSchema instances.
        """
        return list(self._loaded_tools.values())

    def validate_tool(self, module_path: str, class_name: str) -> ToolLoadResult:
        """Validate a tool module without loading it.

        Args:
            module_path: Python module path.
            class_name: Tool class name.

        Returns:
            ToolLoadResult with validation status.
        """
        try:
            module = importlib.import_module(module_path)
        except ImportError as exc:
            return ToolLoadResult(
                success=False,
                errors=[f"Import error: {exc}"],
                module_path=module_path,
            )

        errors = self._validate_tool_class(module, class_name)
        is_valid = len(errors) == 0

        if is_valid:
            schema = self._extract_tool_schema(module, class_name)
            return ToolLoadResult(
                success=True,
                schema=schema,
                module_path=module_path,
            )
        else:
            return ToolLoadResult(
                success=False,
                errors=errors,
                module_path=module_path,
            )

    def needs_reload(self) -> bool:
        """Check if tools need to be reloaded based on file modifications.

        Returns:
            True if any tool module has been modified since last scan.
        """
        if not self._tools_dir.exists():
            return False

        current_time = self._get_current_time()
        if current_time - self._last_scan_time < 5.0:  # Don't check more than once per 5 seconds
            return False

        for module_info in pkgutil.iter_modules([str(self._tools_dir)]):
            if module_info.name.startswith("_"):
                continue
            module_path = self._tools_dir / f"{module_info.name}.py"
            if module_path.exists():
                mtime = module_path.stat().st_mtime
                cached_mtime = self._module_cache.get(module_info.name, 0)
                if mtime > cached_mtime:
                    return True

        return False

    # ------------------------------------------------------------------
    # Internal methods
    # ------------------------------------------------------------------

    def _load_module(
        self,
        module_path: str,
        module_name: str,
    ) -> ToolLoadResult:
        """Load and validate a tool module.

        Args:
            module_path: Full Python module path.
            module_name: Simple module name.

        Returns:
            ToolLoadResult with validation status.
        """
        try:
            # Check cache first
            if module_path in self._module_cache:
                module = self._module_cache[module_path]
            else:
                module = importlib.import_module(module_path)
                self._module_cache[module_path] = module

            # Find tool classes in module
            tool_classes = self._find_tool_classes(module)

            if not tool_classes:
                return ToolLoadResult(
                    success=False,
                    errors=["No tool classes found in module"],
                    module_path=module_path,
                )

            results: list[ToolLoadResult] = []
            for cls_name, cls in tool_classes:
                errors = self._validate_tool_class(module, cls_name)
                if errors:
                    results.append(ToolLoadResult(
                        success=False,
                        errors=errors,
                        module_path=module_path,
                    ))
                    continue

                schema = self._extract_tool_schema(module, cls_name)
                self._loaded_tools[schema.tool_name] = schema
                self._tool_classes[schema.tool_name] = cls
                results.append(ToolLoadResult(
                    success=True,
                    schema=schema,
                    module_path=module_path,
                ))
                logger.info("Loaded tool: %s from %s", schema.tool_name, module_path)

            return results[0] if results else ToolLoadResult(
                success=False,
                errors=["No valid tools found"],
                module_path=module_path,
            )

        except ImportError as exc:
            return ToolLoadResult(
                success=False,
                errors=[f"Import error: {exc}"],
                module_path=module_path,
            )
        except Exception as exc:
            logger.error("Failed to load module %s: %s", module_path, exc, exc_info=True)
            return ToolLoadResult(
                success=False,
                errors=[f"Load error: {exc}"],
                module_path=module_path,
            )

    def _find_tool_classes(
        self,
        module: Any,
    ) -> list[tuple[str, type]]:
        """Find tool classes in a module.

        Args:
            module: Python module to inspect.

        Returns:
            List of (class_name, class) tuples.
        """
        tool_classes = []
        for name, obj in inspect.getmembers(module, inspect.isclass):
            # Check if class has required attributes
            if not hasattr(obj, "execute"):
                continue
            if not (hasattr(obj, "tool_name") or hasattr(obj, "TOOL_NAME")):
                continue
            tool_classes.append((name, obj))
        return tool_classes

    def _validate_tool_class(
        self,
        module: Any,
        class_name: str,
    ) -> list[str]:
        """Validate a tool class has the required interface.

        Args:
            module: Python module containing the class.
            class_name: Name of the class to validate.

        Returns:
            List of validation errors (empty if valid).
        """
        errors: list[str] = []
        cls = getattr(module, class_name, None)

        if cls is None:
            return [f"Class {class_name} not found in module"]

        # Check required attributes
        if not hasattr(cls, "tool_name"):
            errors.append("Missing required attribute: tool_name")
        elif not isinstance(cls.tool_name, str) or not cls.tool_name.strip():
            errors.append("tool_name must be a non-empty string")

        if not hasattr(cls, "description"):
            errors.append("Missing required attribute: description")
        elif not isinstance(cls.description, str) or not cls.description.strip():
            errors.append("description must be a non-empty string")

        # Check execute method
        if not hasattr(cls, "execute"):
            errors.append("Missing required method: execute")
        else:
            execute_method = getattr(cls, "execute")
            if not inspect.iscoroutinefunction(execute_method):
                errors.append("execute method must be async")

            # Check execute signature
            sig = inspect.signature(execute_method)
            params = list(sig.parameters.keys())
            if "tenant_id" not in params:
                errors.append("execute method must accept tenant_id parameter")

        return errors

    def _extract_tool_schema(
        self,
        module: Any,
        class_name: str,
    ) -> ToolSchema:
        """Extract tool schema from a validated tool class.

        Args:
            module: Python module containing the class.
            class_name: Name of the class.

        Returns:
            ToolSchema with extracted metadata.
        """
        cls = getattr(module, class_name)
        tool_name = getattr(cls, "tool_name")
        description = getattr(cls, "description", "")

        # Extract input schema from execute signature
        execute_method = getattr(cls, "execute")
        sig = inspect.signature(execute_method)
        input_schema: dict[str, Any] = {}
        for param_name, param in sig.parameters.items():
            if param_name in ("self", "tenant_id"):
                continue
            annotation = param.annotation
            default = param.default if param.default is not inspect.Parameter.empty else None

            schema_type = self._type_to_json_schema(annotation)
            input_schema[param_name] = {
                "type": schema_type,
                "description": default if isinstance(default, str) else "",
                "default": default if default is not inspect.Parameter.empty else None,
            }

        is_async = inspect.iscoroutinefunction(execute_method)

        # Try to extract output schema from docstring or return annotation
        output_schema: Optional[dict[str, Any]] = None
        if execute_method.__annotations__ and "return" in execute_method.__annotations__:
            return_annotation = execute_method.__annotations__["return"]
            if return_annotation is not inspect.Parameter.empty:
                output_schema = {"type": self._type_to_json_schema(return_annotation)}

        return ToolSchema(
            tool_name=tool_name,
            description=description,
            input_schema=input_schema,
            output_schema=output_schema,
            is_async=is_async,
            module_path=f"{module.__name__}.{class_name}",
            class_name=class_name,
            version=getattr(cls, "version", "1.0.0"),
            author=getattr(cls, "author", None),
            tags=getattr(cls, "tags", []),
        )

    def _instantiate_tool(
        self,
        schema: ToolSchema,
        tenant_id: str,
    ) -> Optional[Any]:
        """Instantiate a tool class.

        Args:
            schema: Tool schema.
            tenant_id: Tenant ID for the instance.

        Returns:
            Tool instance or None if instantiation failed.
        """
        try:
            module = importlib.import_module(schema.module_path.rsplit(".", 1)[0])
            cls = getattr(module, schema.class_name)
            return cls(tenant_id=tenant_id)
        except Exception as exc:
            logger.error(
                "Failed to instantiate tool %s: %s",
                schema.tool_name,
                exc,
                exc_info=True,
            )
            return None

    @staticmethod
    def _type_to_json_schema(annotation: Any) -> str:
        """Map Python type annotation to JSON Schema type string."""
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
        if annotation is Any:
            return "string"  # fallback
        return "string"

    @staticmethod
    def _get_current_time() -> float:
        """Get current timestamp."""
        import time
        return time.monotonic()
