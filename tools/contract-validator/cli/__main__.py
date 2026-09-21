"""Universal Contract Validator CLI — validate data against frozen schemas."""
from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

from services.core.src.contracts.registry import SchemaRegistry

logger = logging.getLogger(__name__)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="contract-validator",
        description="Validate data against Universal Contract v1.0 schemas",
    )
    parser.add_argument(
        "command",
        choices=["validate", "diff", "list", "version"],
        help="Command to execute",
    )
    parser.add_argument(
        "--schema", "-s",
        help="Schema name (Asset, Point, Capability, Relationship, AssetTemplate, CompositeAsset)",
    )
    parser.add_argument(
        "--data", "-d",
        help="Path to data file (JSON/YAML) to validate",
    )
    parser.add_argument(
        "--schema-dir",
        help="Path to schema directory (default: packages/schemas/universal)",
    )
    parser.add_argument(
        "--output", "-o",
        help="Output file for results (default: stdout)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Strict mode: reject additional properties",
    )
    return parser


def cmd_validate(args: argparse.Namespace) -> int:
    """Validate data against a schema."""
    registry = SchemaRegistry()
    schema_dir = Path(args.schema_dir) if args.schema_dir else None
    registry.load(schema_dir)

    if not args.schema:
        print("Error: --schema is required", file=sys.stderr)
        return 1

    if not args.data:
        print("Error: --data is required", file=sys.stderr)
        return 1

    # Load data
    try:
        with open(args.data, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        print(json.dumps({"valid": False, "errors": [f"JSON parse error: {e}"]}))
        return 1
    except FileNotFoundError:
        print(json.dumps({"valid": False, "errors": [f"File not found: {args.data}"]}))
        return 1

    # Validate
    valid, errors = registry.validate_against_schema(args.schema, data)

    result = {
        "valid": valid,
        "schema": args.schema,
        "data_file": args.data,
        "errors": errors,
    }

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2)
    else:
        print(json.dumps(result, indent=2))

    return 0 if valid else 1


def cmd_diff(args: argparse.Namespace) -> int:
    """Compute semantic diff between frozen schema and new schema."""
    registry = SchemaRegistry()
    schema_dir = Path(args.schema_dir) if args.schema_dir else None
    registry.load(schema_dir)

    if not args.schema:
        print("Error: --schema is required", file=sys.stderr)
        return 1

    if not args.data:
        print("Error: --data is required", file=sys.stderr)
        return 1

    try:
        with open(args.data, "r", encoding="utf-8") as f:
            new_schema = json.load(f)
    except (json.JSONDecodeError, FileNotFoundError) as e:
        print(json.dumps({"error": str(e)}))
        return 1

    diff = registry.diff(args.schema, new_schema)

    result = {
        "schema": args.schema,
        "frozen_version": registry.get_version(args.schema),
        "diff": diff,
        "is_zero_diff": len(diff) == 0,
    }

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2)
    else:
        print(json.dumps(result, indent=2))

    return 0 if diff == {} else 1


def cmd_list(args: argparse.Namespace) -> int:
    """List all registered schemas."""
    registry = SchemaRegistry()
    schema_dir = Path(args.schema_dir) if args.schema_dir else None
    registry.load(schema_dir)

    result = {
        "schemas": {
            name: {
                "version": registry.get_version(name),
                "loaded": name in registry._schemas,
            }
            for name in ["Asset", "Point", "Capability", "Relationship", "AssetTemplate", "CompositeAsset"]
        }
    }

    print(json.dumps(result, indent=2))
    return 0


def cmd_version(args: argparse.Namespace) -> int:
    """Print contract version info."""
    registry = SchemaRegistry()
    registry.load()
    result = {
        "contract_version": "1.0.0",
        "status": "FROZEN",
        "schemas": {
            name: registry.get_version(name)
            for name in ["Asset", "Point", "Capability", "Relationship", "AssetTemplate", "CompositeAsset"]
        },
    }
    print(json.dumps(result, indent=2))
    return 0


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    commands = {
        "validate": cmd_validate,
        "diff": cmd_diff,
        "list": cmd_list,
        "version": cmd_version,
    }

    return commands[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
