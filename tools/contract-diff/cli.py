"""Contract Diff Tool — Semantic diff between Contract schema versions."""
from __future__ import annotations

import json
import sys
import argparse
from pathlib import Path
from typing import Any


def compute_diff(baseline: dict[str, Any], target: dict[str, Any]) -> dict[str, Any]:
    """Compute semantic diff between two Contract schema sets."""
    added, removed, modified = [], [], []

    b_keys, t_keys = set(baseline.keys()), set(target.keys())
    added = list(t_keys - b_keys)
    removed = list(b_keys - t_keys)

    for key in b_keys & t_keys:
        b = baseline[key]
        t = target[key]
        if _schema_diff(b, t):
            modified.append(key)

    return {
        "added_fields": added,
        "removed_fields": removed,
        "modified_schemas": modified,
        "semantic_diff": {"added": added, "removed": removed, "modified": modified},
        "is_frozen": len(added) == 0 and len(removed) == 0 and len(modified) == 0,
    }


def _schema_diff(s1: dict, s2: dict) -> bool:
    """Deep compare two JSON schemas for semantic changes."""
    if s1.get("required") != s2.get("required"):
        return True
    for prop, defn in s1.get("properties", {}).items():
        t_defn = s2.get("properties", {}).get(prop)
        if t_defn is None:
            return True
        if defn.get("enum") != t_defn.get("enum"):
            return True
        if defn.get("pattern") != t_defn.get("pattern"):
            return True
        if defn.get("type") != t_defn.get("type"):
            return True
    for prop in s2.get("properties", {}):
        if prop not in s1.get("properties", {}):
            return True
    return False


def main() -> int:
    parser = argparse.ArgumentParser(description="Contract Semantic Diff Tool")
    parser.add_argument("--baseline", required=True, help="Path to baseline JSON schema")
    parser.add_argument("--target", required=True, help="Path to target JSON schema")
    parser.add_argument("--output", help="Output file for diff result")
    args = parser.parse_args()

    with open(args.baseline) as f:
        baseline = json.load(f)
    with open(args.target) as f:
        target = json.load(f)

    diff = compute_diff(baseline, target)

    if args.output:
        with open(args.output, "w") as f:
            json.dump(diff, f, indent=2)

    print(json.dumps(diff, indent=2))
    return 0 if diff["is_frozen"] else 1


if __name__ == "__main__":
    sys.exit(main())
