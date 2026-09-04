"""Schema validator — validates TwinTemplate.schema_definition JSON."""
from typing import Any


VALID_DATA_TYPES = {"string", "integer", "float", "boolean", "datetime", "json"}


class SchemaValidator:
    """Validates the schema_definition field of a TwinTemplate."""

    @staticmethod
    def validate(schema_definition: dict[str, Any]) -> list[str]:
        """Validate schema_definition structure.

        Returns a list of error messages. Empty list means valid.
        """
        errors: list[str] = []

        if not isinstance(schema_definition, dict):
            return ["schema_definition must be a dictionary"]

        # Check for properties key
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

        for idx, prop in enumerate(properties):
            prop_errors = SchemaValidator._validate_property(prop, idx)
            errors.extend(prop_errors)

        return errors

    @classmethod
    def _validate_property(cls, prop: Any, index: int) -> list[str]:
        """Validate a single property definition."""
        errors: list[str] = []
        prefix = f"properties[{index}]"

        if not isinstance(prop, dict):
            return [f"{prefix}: must be a dictionary"]

        # Name is required
        name = prop.get("name")
        if not name or not isinstance(name, str):
            errors.append(f"{prefix}.name: required and must be a string")
        elif not name.strip():
            errors.append(f"{prefix}.name: cannot be empty")

        # Data type is required
        data_type = prop.get("data_type")
        if not data_type or not isinstance(data_type, str):
            errors.append(f"{prefix}.data_type: required and must be a string")
        elif data_type.lower() not in VALID_DATA_TYPES:
            errors.append(
                f"{prefix}.data_type: '{data_type}' not in {VALID_DATA_TYPES}"
            )

        # Optional fields validation
        unit = prop.get("unit")
        if unit is not None and not isinstance(unit, str):
            errors.append(f"{prefix}.unit: must be a string if provided")

        required = prop.get("required")
        if required is not None and not isinstance(required, bool):
            errors.append(f"{prefix}.required: must be a boolean if provided")

        default_value = prop.get("default_value")
        if default_value is not None and not isinstance(default_value, (str, int, float, bool, type(None))):
            errors.append(f"{prefix}.default_value: invalid type")

        return errors
