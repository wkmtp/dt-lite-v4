"""ModelBindingService — Asset ↔ ModelObject binding management.

Enforces SL-10: ModelObject ≠ Asset Identity.
Deleting a BIM element / GIS feature / 3D node MUST NOT cascade-delete the Asset.
FK: model_binding.asset_id → Asset.id (ON DELETE SET NULL)
"""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

logger = logging.getLogger(__name__)

VALID_SOURCES = {"bim", "gis", "3d"}
VALID_SOURCE_TYPES: dict[str, set[str]] = {
    "bim": {"ifc_element", "ifc_space", "ifc_zone"},
    "gis": {"geojson_feature", "geojson_boundary", "geojson_point"},
    "3d": {"gltf_node", "gltf_scene", "gltf_asset"},
}


@dataclass
class ModelBinding:
    """Binding between an Asset and a ModelObject (BIM/GIS/3D).

    Identity boundary: deleting the ModelObject does NOT delete the Asset.
    FK ON DELETE SET NULL ensures binding.asset_id becomes null, not cascade.
    """
    id: str
    asset_id: str
    source: str  # bim | gis | 3d
    source_id: str  # IFC GUID | GeoJSON feature id | glTF node id
    source_type: str = ""
    transform: dict[str, Any] = field(default_factory=dict)
    lod: int = 300  # 100-500
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def created_at(self) -> str:
        return self.metadata.get("created_at", "")

    @property
    def is_nullified(self) -> bool:
        """True when asset_id has been SET NULL (ModelObject was deleted)."""
        return self.asset_id == ""


class ModelBindingService:
    """ModelBinding service: CRUD, identity boundary enforcement.

    NO BIM parsing — that belongs to external IFC parsers.
    NO GIS coordinate transforms — caller provides pre-transformed coords.
    NO 3D rendering — that belongs to ThreeRuntime.
    """

    def __init__(self) -> None:
        self._bindings: dict[str, ModelBinding] = {}
        # Track asset_id → list of binding ids for cascade on asset delete
        self._by_asset: dict[str, list[str]] = {}

    def create(
        self,
        asset_id: str,
        source: str,
        source_id: str,
        source_type: str = "",
        transform: Optional[dict[str, Any]] = None,
        lod: int = 300,
        metadata: Optional[dict[str, Any]] = None,
    ) -> ModelBinding:
        """Create a model binding. Validates SL-10 identity boundary."""
        if source not in VALID_SOURCES:
            raise ValueError(
                f"Invalid source '{source}'. Must be one of: {sorted(VALID_SOURCES)}"
            )

        if source_type:
            allowed = VALID_SOURCE_TYPES.get(source, set())
            if source_type not in allowed:
                raise ValueError(
                    f"Invalid source_type '{source_type}' for source '{source}'. "
                    f"Allowed: {sorted(allowed)}"
                )

        if not isinstance(lod, int) or lod < 100 or lod > 500:
            raise ValueError("lod must be an integer between 100 and 500")

        binding_id = str(uuid.uuid4())
        binding = ModelBinding(
            id=binding_id,
            asset_id=asset_id,
            source=source,
            source_id=source_id,
            source_type=source_type,
            transform=transform or {},
            lod=lod,
            metadata={
                "tenant_id": metadata.get("tenant_id", "") if metadata else "",
                "created_at": datetime.now(timezone.utc).isoformat(),
                **(metadata or {}),
            },
        )
        self._bindings[binding_id] = binding
        self._by_asset.setdefault(asset_id, []).append(binding_id)
        logger.info(
            "Created binding: %s asset=%s source=%s source_id=%s lod=%d",
            binding_id, asset_id, source, source_id, lod,
        )
        return binding

    def get(self, binding_id: str) -> Optional[ModelBinding]:
        """Get binding by ID."""
        return self._bindings.get(binding_id)

    def list_by_asset(self, asset_id: str) -> list[ModelBinding]:
        """List all bindings for an asset."""
        ids = self._by_asset.get(asset_id, [])
        return [self._bindings[bid] for bid in ids if bid in self._bindings]

    def list_by_source(self, source: str) -> list[ModelBinding]:
        """List all bindings of a given source type."""
        return [b for b in self._bindings.values() if b.source == source]

    def nullify(self, binding_id: str) -> Optional[ModelBinding]:
        """Nullify binding.asset_id — called when ModelObject is deleted.

        This is the KEY operation enforcing SL-10:
        - Asset is NOT deleted
        - binding.asset_id is set to empty string (NULL equivalent)
        """
        binding = self._bindings.get(binding_id)
        if not binding:
            return None
        binding.asset_id = ""
        binding.metadata["nullified_at"] = datetime.now(timezone.utc).isoformat()
        binding.metadata["nullified_reason"] = "model_object_deleted"
        logger.info(
            "Nullified binding: %s (asset_id set to NULL) — SL-10 enforced",
            binding_id,
        )
        return binding

    def delete(self, binding_id: str) -> bool:
        """Delete a binding record entirely."""
        binding = self._bindings.get(binding_id)
        if not binding:
            return False
        # Remove from asset index
        asset_bindings = self._by_asset.get(binding.asset_id, [])
        if binding_id in asset_bindings:
            asset_bindings.remove(binding_id)
        del self._bindings[binding_id]
        logger.info("Deleted binding: %s", binding_id)
        return True

    def delete_by_asset(self, asset_id: str) -> int:
        """Delete ALL bindings for an asset — called when Asset is deleted.

        This is the REVERSE direction of SL-10:
        - Asset deletion → bindings are removed (ON DELETE CASCADE on asset side)
        - Binding deletion → asset is NOT removed (ON DELETE SET NULL on binding side)
        """
        ids = self._by_asset.pop(asset_id, [])
        for bid in ids:
            if bid in self._bindings:
                del self._bindings[bid]
        logger.info("Deleted %d bindings for asset %s", len(ids), asset_id)
        return len(ids)

    def count(self) -> int:
        return len(self._bindings)
