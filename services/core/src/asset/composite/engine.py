"""Composite Asset Engine — Tree+Graph composition, capability inheritance, aggregation."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)

MAX_TREE_DEPTH = 10
MAX_GRAPH_EDGES = 1000

AGGREGATION_FUNCTIONS = {"sum", "avg", "min", "max", "count", "latest", "weighted_avg", "custom_expr"}


@dataclass
class CompositionNode:
    """A node in the composite asset tree."""
    ref: str  # child asset ID
    type: str  # relationship type
    depth: int = 1
    weight: float = 1.0  # for weighted_avg


@dataclass
class CompositeAsset:
    """Composite asset with tree+graph topology."""
    id: str
    code: str
    name: str
    composition_tree: list[CompositionNode] = field(default_factory=list)
    capability_inheritance: list[str] = field(default_factory=list)
    aggregation_rules: dict[str, dict[str, Any]] = field(default_factory=dict)
    conflicts: list[dict[str, Any]] = field(default_factory=list)


class CompositeAssetEngine:
    """
    Composite Asset Engine: tree+graph composition, capability inheritance, 8 aggregation functions.
    NO persistence — returns computed results.
    """

    def __init__(self) -> None:
        self._composite_assets: dict[str, CompositeAsset] = {}

    def create(
        self,
        id: str,
        code: str,
        name: str,
        children: list[dict[str, Any]],
        aggregation_rules: Optional[dict[str, dict[str, Any]]] = None,
    ) -> CompositeAsset:
        """Create a composite asset with tree+graph topology."""
        nodes = []
        for child in children:
            node = CompositionNode(
                ref=child["ref"],
                type=child.get("type", "contains"),
                depth=child.get("depth", 1),
                weight=child.get("weight", 1.0),
            )
            if node.depth > MAX_TREE_DEPTH:
                raise ValueError(f"Tree depth {node.depth} exceeds max {MAX_TREE_DEPTH}")
            nodes.append(node)

        # Validate graph edges
        total_edges = len(nodes)
        if total_edges > MAX_GRAPH_EDGES:
            raise ValueError(f"Edge count {total_edges} exceeds max {MAX_GRAPH_EDGES}")

        rules = aggregation_rules or {}
        for key, rule in rules.items():
            if "function" in rule and rule["function"] not in AGGREGATION_FUNCTIONS:
                raise ValueError(f"Invalid aggregation function: {rule['function']}")

        composite = CompositeAsset(
            id=id,
            code=code,
            name=name,
            composition_tree=nodes,
            aggregation_rules=rules,
        )
        self._composite_assets[id] = composite
        logger.info("Created composite asset: %s (%s)", id, code)
        return composite

    def get(self, composite_id: str) -> Optional[CompositeAsset]:
        """Get composite asset by ID."""
        return self._composite_assets.get(composite_id)

    def compute_aggregation(
        self,
        composite_id: str,
        values: dict[str, dict[str, float]],
    ) -> dict[str, float]:
        """
        Compute aggregated KPIs from child asset values.
        values: {child_id: {property_code: value}}
        """
        composite = self._composite_assets.get(composite_id)
        if not composite:
            raise ValueError(f"Composite asset not found: {composite_id}")

        results: dict[str, float] = {}
        for kpi, rule in composite.aggregation_rules.items():
            func = rule["function"]
            child_values = [
                v.get(kpi, 0.0)
                for node in composite.composition_tree
                for v in [values.get(node.ref, {})]
                if v.get(kpi) is not None
            ]

            if func == "sum":
                results[kpi] = sum(child_values) if child_values else 0.0
            elif func == "avg":
                results[kpi] = sum(child_values) / len(child_values) if child_values else 0.0
            elif func == "min":
                results[kpi] = min(child_values) if child_values else 0.0
            elif func == "max":
                results[kpi] = max(child_values) if child_values else 0.0
            elif func == "count":
                results[kpi] = float(len(child_values))
            elif func == "latest":
                results[kpi] = child_values[-1] if child_values else 0.0
            elif func == "weighted_avg":
                total_weight = sum(
                    node.weight for node in composite.composition_tree
                    if values.get(node.ref, {}).get(kpi) is not None
                )
                if total_weight > 0:
                    weighted_sum = sum(
                        values.get(node.ref, {}).get(kpi, 0.0) * node.weight
                        for node in composite.composition_tree
                        if values.get(node.ref, {}).get(kpi) is not None
                    )
                    results[kpi] = weighted_sum / total_weight
                else:
                    results[kpi] = 0.0
            elif func == "custom_expr":
                # Placeholder for DSL evaluation
                results[kpi] = sum(child_values) if child_values else 0.0

        return results

    def compute_capability_inheritance(
        self,
        composite_id: str,
        child_capabilities: dict[str, list[str]],
    ) -> tuple[list[str], list[dict[str, Any]]]:
        """
        Compute inherited capabilities with LIFO override + conflict resolution.
        Returns (inherited_capabilities, conflicts).
        """
        composite = self._composite_assets.get(composite_id)
        if not composite:
            raise ValueError(f"Composite asset not found: {composite_id}")

        inherited: dict[str, str] = {}  # code → source_asset_id
        conflicts: list[dict[str, Any]] = []

        # LIFO: process children in order, last one wins
        for node in composite.composition_tree:
            child_caps = child_capabilities.get(node.ref, [])
            for cap_code in child_caps:
                if cap_code in inherited:
                    # Conflict: same capability from multiple children
                    conflicts.append({
                        "capability_code": cap_code,
                        "previous_source": inherited[cap_code],
                        "new_source": node.ref,
                        "resolution": "lifo_override",
                    })
                inherited[cap_code] = node.ref

        return list(inherited.keys()), conflicts

    def validate_tree_acyclic(self, composite_id: str, asset_children: dict[str, list[str]]) -> bool:
        """
        Validate that the tree is acyclic using DFS.
        asset_children: {asset_id: [child_ids]}
        """
        composite = self._composite_assets.get(composite_id)
        if not composite:
            return False

        visited: set[str] = set()
        rec_stack: set[str] = set()

        def has_cycle(node_id: str) -> bool:
            visited.add(node_id)
            rec_stack.add(node_id)
            for child_id in asset_children.get(node_id, []):
                if child_id not in visited:
                    if has_cycle(child_id):
                        return True
                elif child_id in rec_stack:
                    return True
            rec_stack.discard(node_id)
            return False

        for node in composite.composition_tree:
            if node.ref not in visited:
                if has_cycle(node.ref):
                    return False
        return True
