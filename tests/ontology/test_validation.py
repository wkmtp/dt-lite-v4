"""Test ontology schema validation."""

from services.ontology.validators import CapabilitySchemaValidator, EntityTypeValidator


class TestCapabilitySchemaValidator:
    """Test capability schema validation rules."""

    def test_valid_schema_accepted(self):
        """Valid capability schema should pass."""
        schema = {
            "version": "1.0",
            "properties": [
                {"name": "temperature", "data_type": "float", "unit": "celsius"},
                {"name": "status", "data_type": "string"},
            ],
        }
        errors = CapabilitySchemaValidator.validate(schema)
        assert errors == [], f"Valid schema rejected: {errors}"

    def test_invalid_data_type_rejected(self):
        """Unknown data types must be rejected."""
        schema = {
            "version": "1.0",
            "properties": [
                {"name": "value", "data_type": "superstring"},
            ],
        }
        errors = CapabilitySchemaValidator.validate(schema)
        assert len(errors) > 0
        assert "data_type" in errors[0].lower()

    def test_empty_property_name_rejected(self):
        """Properties with empty names must be rejected."""
        schema = {
            "properties": [
                {"name": "", "data_type": "float"},
            ],
        }
        errors = CapabilitySchemaValidator.validate(schema)
        assert len(errors) > 0

    def test_missing_properties_key_rejected(self):
        """Schema without 'properties' key must be rejected."""
        schema = {"version": "1.0"}
        errors = CapabilitySchemaValidator.validate(schema)
        assert len(errors) > 0
        assert "properties" in errors[0].lower()

    def test_duplicate_property_name_rejected(self):
        """Duplicate property names within same schema must be rejected."""
        schema = {
            "version": "1.0",
            "properties": [
                {"name": "temperature", "data_type": "float"},
                {"name": "temperature", "data_type": "integer"},
            ],
        }
        errors = CapabilitySchemaValidator.validate(schema)
        assert len(errors) > 0
        assert "duplicate" in errors[0].lower()

    def test_missing_version_rejected(self):
        """Schema without version must be rejected."""
        schema = {"properties": [{"name": "temp", "data_type": "float"}]}
        errors = CapabilitySchemaValidator.validate(schema)
        assert len(errors) > 0
        assert "version" in errors[0].lower()

    def test_empty_properties_list_rejected(self):
        """Empty properties array must be rejected."""
        schema = {"version": "1.0", "properties": []}
        errors = CapabilitySchemaValidator.validate(schema)
        assert len(errors) > 0
        assert "at least one" in errors[0].lower()

    def test_non_dict_properties_rejected(self):
        """Non-dictionary properties must be rejected."""
        schema = {"properties": ["invalid"]}
        errors = CapabilitySchemaValidator.validate(schema)
        assert len(errors) > 0


class TestEntityTypeValidator:
    """Test entity type property schema validation."""

    def test_valid_property_schema_accepted(self):
        """Valid property schema should pass."""
        errors = EntityTypeValidator.validate_property_schema({"properties": []})
        assert errors == []

    def test_empty_property_schema_accepted(self):
        """Empty property schema is valid (no predefined properties)."""
        errors = EntityTypeValidator.validate_property_schema({})
        assert errors == []

    def test_invalid_property_schema_rejected(self):
        """Invalid property schema structure should be rejected."""
        errors = EntityTypeValidator.validate_property_schema("not_a_dict")
        assert len(errors) > 0

    def test_missing_property_name_rejected(self):
        """Property definition missing name must be rejected."""
        schema = {"properties": [{"data_type": "float"}]}
        errors = EntityTypeValidator.validate_property_schema(schema)
        assert len(errors) > 0
        assert "name" in errors[0].lower()
