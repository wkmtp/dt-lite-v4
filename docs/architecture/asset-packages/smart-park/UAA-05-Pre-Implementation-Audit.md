# UAA-05 Pre-Implementation Audit

**Task**: UAA-05: Scene, BIM, GIS & 3D
**Date**: 2026-09-13
**Base Line**: Universal Asset Assembly Contract v1.0 (FROZEN)
**Predecessors**: UAA-01 (Contract Registry) + UAA-02 (Asset Services) + UAA-03 (Point/Capability) + UAA-04 (External Integration)

---

## 1. Architecture Gate Target

| Gate | Check | Expected |
|------|-------|----------|
| **AG-P0-06** | BIM/GIS/3D Identity Boundary | ON DELETE SET NULL on FK model_binding.asset_id |
| **AG-P1-01** | Unit Test Coverage ≥ 80% | Core services only |
| **AG-P1-02** | Integration Test Coverage ≥ 70% | API contracts |

## 2. Scope Lock Compliance Checklist

| SL | Prohibition | UAA-05 Compliance |
|----|-------------|-------------------|
| SL-01 | No new fields in Universal Contract Objects | ✅ Scene/Binding are NEW objects, not modifications to existing 31 Contract Objects |
| SL-02 | No renaming/removing Universal Contract fields | ✅ Only adds `model_bindings[]` to Asset (already defined in UAA-01 schema) |
| SL-03 | No mandatory industry fields in Universal Contract | ✅ Scene types are generic, not industry-specific |
| SL-04 | No protocol address in Point | ✅ Scene/BIM/GIS/3D do not touch Point protocol fields |
| SL-05 | No algorithm in Capability | ✅ 3D runtime visual mapping is rendering logic, not Capability |
| SL-09 | No Dashboard/LargeScreen conflation | ✅ Scene ≠ Dashboard; Scene is 3D spatial context, Dashboard is interactive widgets |
| SL-10 | No ModelObject=Asset identity conflation | ✅ HARD RULE: `Asset.id ≠ ModelObject.id`; FK ON DELETE SET NULL |
| SL-12 | No weakening Contract constraints | ✅ All existing constraints preserved |

## 3. Scene Contract (10 Types)

| Scene Type | Description | Key Features |
|------------|-------------|--------------|
| **overview** | Park/factory-wide 3D overview | Zoomed-out camera, multi-layer, no asset-specific filters |
| **energy** | Energy monitoring | Power flow visualization, real-time telemetry-driven color |
| **hvac** | HVAC system overview | AHU/FCU/chiller relationships, airflow layers |
| **water** | Water management | Pipeline network, flow rates, tank levels |
| **security** | Security operations | Camera zones, access points, alarm heatmap |
| **transport** | Transport & parking | Vehicle tracking, parking occupancy, traffic flow |
| **environment** | Environment monitoring | Air quality, noise, temperature heatmap |
| **production** | Production line | Machine status, OEE, work-in-progress |
| **fire** | Fire safety | Zone overview, alarm status, evacuation routes |
| **custom** | User-defined | Any combination of above with custom layout |

**Scene Schema Fields** (new, not part of 31 frozen objects):
- `id` (UUID)
- `code` (string, pattern: `^scene\.(park|factory)\.[a-z_][a-z0-9_]*$`)
- `name` (string)
- `type` (enum: overview, energy, hvac, water, security, transport, environment, production, fire, custom)
- `tenant_id` (UUID)
- `layout` (JSON: layers, camera, filters, permissions)
- `model_bindings` (array: same format as Asset.model_bindings)
- `metadata` (JSONB)

## 4. Model Binding Service

### 4.1 Binding Schema

`Asset.model_bindings[]` contains binding entries:

```json
{
  "id": "uuid",
  "source": "bim",
  "source_id": "IFC_GUID_or_GeoJSON_ID_or_glTF_node_id",
  "source_type": "ifc_element | geojson_feature | gltf_node",
  "transform": {
    "translation": [x, y, z],
    "rotation": [rx, ry, rz],
    "scale": [sx, sy, sz]
  },
  "lod": 300,
  "metadata": {}
}
```

### 4.2 BIM (IFC) Binding
- **Source**: IFC element GUID (GloballyUniqueIdentifier)
- **Property Set Mapping**: IFC → Asset attributes via IfcPropertySet
- **LOD**: 100 (conceptual) → 500 (as-built), integer 100-500
- **Binding Table**: `bim_bindings` — FK to Asset.id (ON DELETE SET NULL)

### 4.3 GIS (GeoJSON) Binding
- **Source**: GeoJSON Feature ID (properties.id or feature.id)
- **Coordinate Transform**: WGS84 ↔ local projected coordinate system
- **Feature Styling**: Color, opacity, height driven by Asset state
- **Binding Table**: `gis_bindings` — FK to Asset.id (ON DELETE SET NULL)

### 4.4 3D (glTF) Binding
- **Source**: glTF Node ID (node.id or node.name)
- **Node Binding**: Asset state → Material color, animation speed/angle
- **Binding Table**: `gltf_bindings` — FK to Asset.id (ON DELETE SET NULL)

## 5. Identity Boundary (HARD RULE — SL-10)

### 5.1 Database Constraint

```sql
-- BIM bindings
ALTER TABLE bim_bindings
  ADD CONSTRAINT fk_bim_binding_asset
    FOREIGN KEY (asset_id) REFERENCES assets(id)
    ON DELETE SET NULL;

-- GIS bindings
ALTER TABLE gis_bindings
  ADD CONSTRAINT fk_gis_binding_asset
    FOREIGN KEY (asset_id) REFERENCES assets(id)
    ON DELETE SET NULL;

-- 3D/gltf bindings
ALTER TABLE gltf_bindings
  ADD CONSTRAINT fk_gltf_binding_asset
    FOREIGN KEY (asset_id) REFERENCES assets(id)
    ON DELETE SET NULL;
```

### 5.2 Test Matrix

| Test | Action | Expected Result |
|------|--------|-----------------|
| IB-01 | DELETE bim_element WHERE guid='X' | Asset still exists; binding.asset_id → NULL |
| IB-02 | DELETE geojson_feature WHERE id='Y' | Asset still exists; binding.asset_id → NULL |
| IB-03 | DELETE gltf_node WHERE id='Z' | Asset still exists; binding.asset_id → NULL |
| IB-04 | DELETE asset WHERE id='A' | All bindings (BIM/GIS/3D) for this asset deleted |

## 6. Three Runtime Integration

### 6.1 Asset State → 3D Visual Mapping

| Asset State | Visual Effect |
|-------------|---------------|
| Point telemetry value | Node color (gradient: green→yellow→red) |
| Capability status (active/alarm) | Animation (rotation speed, pulsing) |
| Asset name/attributes | Tooltip on hover |
| Lifecycle status | Opacity (active=1.0, decommissioned=0.3, retired=0.1) |

### 6.2 Update Pipeline
```
Telemetry Ingest → ThreeRuntime.update(asset_id, state) → 3D scene render
Latency target: ≤ 100ms from ingest to visual update
```

## 7. Service Boundaries

| Service | Responsibility | Forbidden Operations |
|---------|---------------|---------------------|
| **SceneService** | CRUD scene, layout validation, camera config | NO 3D rendering logic, NO asset CRUD |
| **ModelBindingService** | Create/read/update/delete binding, validate FK | NO BIM file parsing, NO GIS coordinate transform |
| **ThreeRuntime** | Asset state → 3D visual mapping, update pipeline | NO database access, NO scene management |

## 8. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| BIM/IFC parsing complexity | Medium | Medium | Use existing IFC parser (ifcOpenFlight or similar); stub for unit tests |
| 3D rendering performance | Medium | Low | Async update queue; throttle to ≤100ms |
| Coordinate transform precision | Low | Medium | Standard library (pyproj or custom affine transform) |
| FK cascade failure | Low | High | Explicit ON DELETE SET NULL + test coverage |

## 9. Pre-Implementation Checklist

### Scene Contract (10 Types)
- [x] overview, energy, hvac, water, security, transport, environment, production, fire, custom

### Model Binding
- [x] Source enum: bim (IFC), gis (GeoJSON), 3d (glTF)
- [x] Transform: translation, rotation, scale (matrix 4x4)
- [x] LOD: 100 (conceptual) to 500 (as-built)

### Identity Boundary (HARD RULE)
- [x] FK: model_binding.asset_id → Asset.id (ON DELETE SET NULL)
- [x] NO cascade delete from ModelObject to Asset
- [x] Test: DELETE FROM bim_elements WHERE guid='X' → Asset still exists, binding.guid = NULL

### 3D Runtime
- [x] Telemetry → Visual mapping: value → color (gradient), value → animation (speed/angle), value → tooltip
- [x] Update rate: ≤ 100ms latency from telemetry ingest to 3D update

## 10. Design Lock Sign-off

| Role | Name | Date | Signature |
|------|------|------|-----------|
| Pre-Implementation Audit | agnes_flash | 2026-09-13 | _(pending)_ |
| Design Lock Review | dt_manager | _(pending)_ | _(pending)_ |
| ARB Final Sign-off | _(pending)_ | _(pending)_ | _(pending)_ |

---

**Design Lock Status**: PENDING REVIEW
