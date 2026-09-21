"""Composite Asset module — Tree+Graph composition, inheritance, aggregation."""
from services.core.src.asset.composite.engine import (
    CompositeAsset,
    CompositionNode,
    CompositeAssetEngine,
    MAX_TREE_DEPTH,
    MAX_GRAPH_EDGES,
    AGGREGATION_FUNCTIONS,
)

__all__ = [
    "CompositeAsset", "CompositionNode", "CompositeAssetEngine",
    "MAX_TREE_DEPTH", "MAX_GRAPH_EDGES", "AGGREGATION_FUNCTIONS",
]
