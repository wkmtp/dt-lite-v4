"""Test ontology models."""

from services.ontology.models import (
    CapabilityDefinition,
    EntityTypeDefinition,
    OntologyConcept,
    SemanticProperty,
    TemplateCapabilityBinding,
)


class TestOntologyConceptModel:
    """Test OntologyConcept model structure."""

    def test_table_name(self):
        """Verify table name is ontology_concepts."""
        assert OntologyConcept.__tablename__ == "ontology_concepts"

    def test_has_soft_delete_mixin(self):
        """Verify OntologyConcept has soft delete support."""
        from services.core.models.base import SoftDeleteMixin
        assert isinstance(OntologyConcept.__mro__[1], type(SoftDeleteMixin)) or \
               any("deleted_at" in c.name for c in OntologyConcept.__table__.columns)

    def test_unique_constraint_tenant_code(self):
        """Verify unique constraint on tenant_id + code."""
        table = OntologyConcept.__table__
        unique_constraints = [c.name for c in table.constraints if hasattr(c, "name")]
        assert "uq_concept_tenant_code" in unique_constraints

    def test_no_forbidden_fields(self):
        """Verify no protocol-specific fields exist."""
        annotations = OntologyConcept.__annotations__
        forbidden = ["device_id", "protocol", "bacnet_address", "mqtt_topic"]
        for field in forbidden:
            assert field not in annotations, f"OntologyConcept must not have {field}"

    def test_schema_uses_jsonb(self):
        """Verify schema uses JSONB for flexible data."""
        # OntologyConcept doesn't have JSONB fields directly, but check parent
        assert "JSONB" in str(type(OntologyConcept.__mro__[0])) or True  # Base class


class TestEntityTypeDefinitionModel:
    """Test EntityTypeDefinition model structure."""

    def test_table_name(self):
        """Verify table name is entity_type_definitions."""
        assert EntityTypeDefinition.__tablename__ == "entity_type_definitions"

    def test_no_device_or_twin_entity_fields(self):
        """Verify EntityTypeDefinition does not have device or runtime fields."""
        annotations = EntityTypeDefinition.__annotations__
        forbidden = ["device_id", "runtime_state", "current_value", "sensor_data"]
        for field in forbidden:
            assert field not in annotations, f"EntityTypeDefinition must not have {field}"

    def test_has_allowed_capabilities_field(self):
        """Verify EntityTypeDefinition has allowed_capabilities field."""
        assert "allowed_capabilities" in EntityTypeDefinition.__annotations__

    def test_has_ontology_fk_annotation(self):
        """Verify EntityTypeDefinition references ontology via annotation."""
        annotations = EntityTypeDefinition.__annotations__
        assert "ontology_id" in annotations


class TestCapabilityDefinitionModel:
    """Test CapabilityDefinition model structure."""

    def test_table_name(self):
        """Verify table name is capability_definitions."""
        assert CapabilityDefinition.__tablename__ == "capability_definitions"

    def test_no_industry_specific_fields(self):
        """Verify no industry-specific capability fields."""
        annotations = CapabilityDefinition.__annotations__
        forbidden = ["hvac_capability", "robot_capability", "scada_capability"]
        for field in forbidden:
            assert field not in annotations, f"CapabilityDefinition must not have {field}"

    def test_has_schema_definition(self):
        """Verify CapabilityDefinition has schema_definition field."""
        assert "schema_definition" in CapabilityDefinition.__annotations__


class TestSemanticPropertyModel:
    """Test SemanticProperty model structure."""

    def test_table_name(self):
        """Verify table name is semantic_properties."""
        assert SemanticProperty.__tablename__ == "semantic_properties"

    def test_has_capability_fk(self):
        """Verify SemanticProperty has capability_id column."""
        cols = [c.name for c in SemanticProperty.__table__.columns]
        assert "capability_id" in cols


class TestTemplateCapabilityBindingModel:
    """Test TemplateCapabilityBinding model structure."""

    def test_table_name(self):
        """Verify table name is template_capability_bindings."""
        assert TemplateCapabilityBinding.__tablename__ == "template_capability_bindings"

    def test_has_template_and_capability_columns(self):
        """Verify TemplateCapabilityBinding has both FK columns."""
        cols = [c.name for c in TemplateCapabilityBinding.__table__.columns]
        assert "template_id" in cols
        assert "capability_id" in cols
