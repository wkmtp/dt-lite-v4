"""Scene Service — Scene CRUD and management.

Scene types: overview, energy, hvac, water, security, transport,
             environment, production, fire, custom.

Scene is a SPATIAL CONTEXT for Assets — NOT an Asset, NOT a Dashboard.
Scene ≡ "a named 3D view configuration with layers, camera, and filters."
"""
from __future__ import annotations

import logging
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

logger = logging.getLogger(__name__)

SCENE_TYPE_PATTERN = re.compile(
    r"^scene\.(park|factory)\.[a-z_][a-z0-9_]*$"
)

VALID_SCENE_TYPES = {
    "overview", "energy", "hvac", "water", "security",
    "transport", "environment", "production", "fire", "custom",
}


@dataclass
class Scene:
    """Scene entity — spatial context for Asset visualization."""
    id: str
    code: str
    name: str
    type: str  # one of VALID_SCENE_TYPES
    tenant_id: str
    layout: dict[str, Any] = field(default_factory=dict)
    model_bindings: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def created_at(self) -> str:
        return self.metadata.get("created_at", "")

    @property
    def layer_count(self) -> int:
        return len(self.layout.get("layers", []))

    @property
    def camera_config(self) -> dict[str, Any]:
        return self.layout.get("camera", {})

    @property
    def filter_config(self) -> dict[str, Any]:
        return self.layout.get("filters", {})


class SceneService:
    """Scene service: CRUD, layout validation, scene type enforcement.

    NO 3D rendering logic — that belongs to ThreeRuntime.
    NO asset CRUD — that belongs to AssetService.
    """

    def __init__(self) -> None:
        self._scenes: dict[str, Scene] = {}

    def create(self, data: dict[str, Any], tenant_id: str) -> Scene:
        """Create a new scene with validation."""
        # Validate required fields
        for key in ["id", "code", "name", "type"]:
            if key not in data:
                raise ValueError(f"Scene missing required field: {key}")

        # Validate code naming convention
        if not SCENE_TYPE_PATTERN.match(data["code"]):
            raise ValueError(
                f"Scene code '{data['code']}' does not match convention: "
                f"scene.<domain>.<type>"
            )

        # Validate scene type
        if data["type"] not in VALID_SCENE_TYPES:
            raise ValueError(
                f"Invalid scene type '{data['type']}'. "
                f"Must be one of: {sorted(VALID_SCENE_TYPES)}"
            )

        # Validate layout structure
        layout = data.get("layout", {})
        self._validate_layout(layout)

        # Validate model_bindings structure
        bindings = data.get("model_bindings", [])
        self._validate_bindings(bindings)

        scene = Scene(
            id=data["id"],
            code=data["code"],
            name=data["name"],
            type=data["type"],
            tenant_id=tenant_id,
            layout=layout,
            model_bindings=bindings,
            metadata={
                "tenant_id": tenant_id,
                "created_at": datetime.now(timezone.utc).isoformat(),
                **data.get("metadata", {}),
            },
        )
        self._scenes[scene.id] = scene
        logger.info("Created scene: %s (%s) type=%s tenant=%s", scene.id, scene.code, scene.type, tenant_id)
        return scene

    def get(self, scene_id: str) -> Optional[Scene]:
        """Get scene by ID."""
        return self._scenes.get(scene_id)

    def list_by_type(self, scene_type: str, tenant_id: str) -> list[Scene]:
        """List scenes filtered by type and tenant."""
        if scene_type not in VALID_SCENE_TYPES:
            raise ValueError(f"Invalid scene type: {scene_type}")
        return [
            s for s in self._scenes.values()
            if s.type == scene_type and s.tenant_id == tenant_id
        ]

    def list_by_tenant(self, tenant_id: str) -> list[Scene]:
        """List all scenes for a tenant."""
        return [s for s in self._scenes.values() if s.tenant_id == tenant_id]

    def update(self, scene_id: str, updates: dict[str, Any]) -> Optional[Scene]:
        """Update scene fields."""
        scene = self._scenes.get(scene_id)
        if not scene:
            return None

        # Validate any layout changes
        if "layout" in updates:
            self._validate_layout(updates["layout"])

        # Validate any model_bindings changes
        if "model_bindings" in updates:
            self._validate_bindings(updates["model_bindings"])

        for key, value in updates.items():
            if hasattr(scene, key) and key not in ("metadata",):
                setattr(scene, key, value)
            elif key == "metadata":
                scene.metadata.update(value)
        return scene

    def delete(self, scene_id: str) -> bool:
        """Delete scene (remove from registry)."""
        if scene_id in self._scenes:
            del self._scenes[scene_id]
            logger.info("Deleted scene: %s", scene_id)
            return True
        return False

    def bind_asset(self, scene_id: str, binding: dict[str, Any]) -> Optional[Scene]:
        """Add a model binding to a scene."""
        scene = self._scenes.get(scene_id)
        if not scene:
            return None
        self._validate_binding(binding)
        scene.model_bindings.append(binding)
        return scene

    def unbind_asset(self, scene_id: str, binding_id: str) -> Optional[Scene]:
        """Remove a model binding from a scene by binding id."""
        scene = self._scenes.get(scene_id)
        if not scene:
            return None
        scene.model_bindings = [
            b for b in scene.model_bindings if b.get("id") != binding_id
        ]
        return scene

    # ── Validation helpers ──────────────────────────────────────────

    def _validate_layout(self, layout: dict[str, Any]) -> None:
        """Validate scene layout structure."""
        if not isinstance(layout, dict):
            raise ValueError("layout must be a JSON object")

        # layers: array of layer objects
        layers = layout.get("layers", [])
        if not isinstance(layers, list):
            raise ValueError("layout.layers must be an array")
        for i, layer in enumerate(layers):
            if not isinstance(layer, dict):
                raise ValueError(f"layout.layers[{i}] must be an object")
            if "id" not in layer:
                raise ValueError(f"layout.layers[{i}] missing 'id'")
            if "visible" not in layer:
                raise ValueError(f"layout.layers[{i}] missing 'visible'")

        # camera: optional object with position/lookAt/fov
        camera = layout.get("camera")
        if camera is not None and not isinstance(camera, dict):
            raise ValueError("layout.camera must be an object")

        # filters: optional array
        filters = layout.get("filters")
        if filters is not None and not isinstance(filters, list):
            raise ValueError("layout.filters must be an array")

    def _validate_bindings(self, bindings: list[Any]) -> None:
        """Validate model_bindings array."""
        if not isinstance(bindings, list):
            raise ValueError("model_bindings must be an array")
        for b in bindings:
            self._validate_binding(b)

    def _validate_binding(self, binding: dict[str, Any]) -> None:
        """Validate a single model binding entry."""
        required = ["id", "source", "source_id"]
        for key in required:
            if key not in binding:
                raise ValueError(f"model_binding missing required field: {key}")

        valid_sources = {"bim", "gis", "3d"}
        if binding["source"] not in valid_sources:
            raise ValueError(
                f"Invalid binding source '{binding['source']}'. "
                f"Must be one of: {sorted(valid_sources)}"
            )

        valid_source_types = {
            "bim": {"ifc_element", "ifc_space", "ifc_zone"},
            "gis": {"geojson_feature", "geojson_boundary", "geojson_point"},
            "3d": {"gltf_node", "gltf_scene", "gltf_asset"},
        }
        source_type = binding.get("source_type")
        if source_type:
            allowed = valid_source_types.get(binding["source"], set())
            if source_type not in allowed:
                raise ValueError(
                    f"Invalid source_type '{source_type}' for source '{binding['source']}'. "
                    f"Allowed: {sorted(allowed)}"
                )

        # lod: 100-500
        lod = binding.get("lod")
        if lod is not None:
            if not isinstance(lod, int) or lod < 100 or lod > 500:
                raise ValueError("lod must be an integer between 100 and 500")

        # transform: optional 4x4 matrix or nested object
        transform = binding.get("transform")
        if transform is not None:
            if isinstance(transform, dict):
                for key in ("translation", "rotation", "scale"):
                    val = transform.get(key)
                    if val is not None and (
                        not isinstance(val, list) or len(val) != 3
                    ):
                        raise ValueError(
                            f"transform.{key} must be a 3-element array [x,y,z]"
                        )
            elif not isinstance(transform, list):
                raise ValueError("transform must be a 4x4 matrix (list of 4 lists) or object")
