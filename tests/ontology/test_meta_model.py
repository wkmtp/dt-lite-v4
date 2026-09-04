"""Test ontology semantic meta model relationships."""
from services.ontology.models import (
    CapabilityDefinition,
    EntityTypeDefinition,
    OntologyConcept,
    SemanticProperty,
    TemplateCapabilityBinding,
)


class TestSemanticModelRelationships:
    """Test semantic model relationships and constraints via introspection."""

    def test_concept_has_children_relationship(self):
        """OntologyConcept should have children relationship defined."""
        annotations = OntologyConcept.__annotations__
        assert "children" in annotations

    def test_concept_has_entity_types_relationship(self):
        """OntologyConcept should link to entity types."""
        annotations = OntologyConcept.__annotations__
        assert "entity_types" in annotations

    def test_entity_type_links_to_ontology(self):
        """EntityTypeDefinition should reference an ontology concept."""
        annotations = EntityTypeDefinition.__annotations__
        assert "ontology_id" in annotations

    def test_capability_has_semantic_properties(self):
        """CapabilityDefinition should link to semantic properties."""
        annotations = CapabilityDefinition.__annotations__
        assert "properties" in annotations

    def test_semantic_property_belongs_to_capability(self):
        """SemanticProperty should link back to capability."""
        annotations = SemanticProperty.__annotations__
        assert "capability_id" in annotations

    def test_template_capability_binding_has_both_fks(self):
        """TemplateCapabilityBinding should link to both template and capability."""
        annotations = TemplateCapabilityBinding.__annotations__
        assert "template_id" in annotations
        assert "capability_id" in annotations


class TestZeroCodeReadiness:
    """Test that meta model supports zero-code twin generation flow."""

    def test_entity_type_has_allowed_capabilities(self):
        """EntityTypeDefinition must have allowed_capabilities field for linking."""
        annotations = EntityTypeDefinition.__annotations__
        assert "allowed_capabilities" in annotations

    def test_template_can_bind_to_capability(self):
        """TemplateCapabilityBinding connects template to capability."""
        annotations = TemplateCapabilityBinding.__annotations__
        assert "template_id" in annotations
        assert "capability_id" in annotations
        assert "required" in annotations

    def test_capability_schema_contains_properties(self):
        """Capability schema_definition must support property array."""
        annotations = CapabilityDefinition.__annotations__
        assert "schema_definition" in annotations

    def test_ontology_hierarchy_support(self):
        """OntologyConcept must support hierarchical parent-child structure."""
        table = OntologyConcept.__table__
        col_names = [c.name for c in table.columns]
        assert "parent_id" in col_names
        assert "id" in col_names  # Self-referential FK
