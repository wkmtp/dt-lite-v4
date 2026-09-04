"""Schema validators for ontology entities."""
from typing import Any


VALID_DATA_TYPES = {"string", "integer", "float", "boolean", "datetime", "json"}


class CapabilitySchemaValidator:
    """Validates CapabilityDefinition.schema_definition JSON structure."""

    @staticmethod
    def validate(schema_definition: dict[str, Any]) -> list[str]:
        """Validate capability schema definition.

        Returns a list of error messages. Empty list means valid.
        """
        errors: list[str] = []

        if not isinstance(schema_definition, dict):
            return ["schema_definition must be a dictionary"]

        # Check required top-level fields
        if "version" not in schema_definition:
            errors.append("schema_definition must contain 'version' field")

        if "properties" not in schema_definition:
            errors.append("schema_definition must contain 'properties' array")
            return errors

        properties = schema_definition.get("properties")
        if not isinstance(properties, list):
            errors.append("'properties' must be an array")
            return errors

        if len(properties) == 0:
            errors.append("'properties' must contain at least one property")
            return errors

        seen_names: set[str] = set()
        for idx, prop in enumerate(properties):
            prop_errors = CapabilitySchemaValidator._validate_property(prop, idx, seen_names)
            errors.extend(prop_errors)

        return errors

    @classmethod
    def _validate_property(cls, prop: Any, index: int, seen_names: set[str]) -> list[str]:
        """Validate a single property in the schema."""
        errors: list[str] = []
        prefix = f"properties[{index}]"

        if not isinstance(prop, dict):
            return [f"{prefix}: must be a dictionary"]

        # Name is required and unique
        name = prop.get("name")
        if not name or not isinstance(name, str):
            errors.append(f"{prefix}.name: required and must be a string")
        elif not name.strip():
            errors.append(f"{prefix}.name: cannot be empty")
        elif name.strip().lower() in seen_names:
            errors.append(f"{prefix}.name: duplicate property name '{name}'")
        else:
            seen_names.add(name.strip().lower())

        # Data type is required
        data_type = prop.get("data_type") or prop.get("type")
        if not data_type or not isinstance(data_type, str):
            errors.append(f"{prefix}.data_type: required and must be a string")
        elif data_type.lower() not in VALID_DATA_TYPES:
            errors.append(
                f"{prefix}.data_type: '{data_type}' not in {VALID_DATA_TYPES}"
            )

        # Optional fields
        unit = prop.get("unit")
        if unit is not None and not isinstance(unit, str):
            errors.append(f"{prefix}.unit: must be a string if provided")

        required = prop.get("required")
        if required is not None and not isinstance(required, bool):
            errors.append(f"{prefix}.required: must be a boolean if provided")

        description = prop.get("description")
        if description is not None and not isinstance(description, str):
            errors.append(f"{prefix}.description: must be a string if provided")

        return errors


class OntologyConceptValidator:
    """Validates ontology concept hierarchy integrity."""

    @staticmethod
    def validate_category(category: str) -> bool:
        """Validate category is one of allowed values."""
        allowed = {"general", "physical", "logical", "spatial", "temporal", "behavioral"}
        return category.lower() in allowed


class EntityTypeValidator:
    """Validates entity type definition structure."""

    @staticmethod
    def validate_property_schema(schema: dict[str, Any]) -> list[str]:
        """Validate entity type property_schema field."""
        errors: list[str] = []

        if not isinstance(schema, dict):
            return ["property_schema must be a dictionary"]

        # property_schema can be empty (no predefined properties)
        if not schema:
            return errors

        # If it has a 'properties' key, validate its structure
        if "properties" in schema:
            props = schema["properties"]
            if not isinstance(props, list):
                errors.append("'properties' in property_schema must be an array")
            else:
                for idx, prop in enumerate(props):
                    if not isinstance(prop, dict):
                        errors.append(f"property_schema.properties[{idx}] must be a dict")
                    elif "name" not in prop:
                        errors.append(f"property_schema.properties[{idx}] missing 'name'")

        return errors
