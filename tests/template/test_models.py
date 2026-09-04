"""Test template models."""
from uuid import UUID, uuid4

from services.template.models import TemplateProperty, TemplateRelationship, TwinTemplate


class TestTwinTemplateModel:
    """Test TwinTemplate model structure."""

    def test_model_creation(self):
        """Verify TwinTemplate can be instantiated."""
        template = TwinTemplate(
            id=uuid4(),
            tenant_id=uuid4(),
            code="building.hvac.ahu",
            name="AHU Unit",
            industry="building",
            version="1.0.0",
            schema_definition={"properties": []},
            status="active",
            deleted_at=None,
        )
        assert template.id is not None
        assert isinstance(template.id, UUID)
        assert template.status == "active"

    def test_table_name(self):
        """Verify table name is twin_templates."""
        assert TwinTemplate.__tablename__ == "twin_templates"

    def test_has_soft_delete_mixin(self):
        """Verify TwinTemplate has soft delete support."""
        template = TwinTemplate(
            id=uuid4(),
            tenant_id=uuid4(),
            code="test.code",
            name="Test",
            industry="general",
        )
        assert hasattr(template, "deleted_at")
        assert template.deleted_at is None

    def test_unique_constraint_tenant_code(self):
        """Verify unique constraint on tenant_id + code."""
        table = TwinTemplate.__table__
        unique_constraints = [c for c in table.constraints if hasattr(c, "columns")]
        constraint_names = [c.name for c in unique_constraints]
        assert "uq_template_tenant_code" in constraint_names

    def test_no_forbidden_fields(self):
        """Verify no protocol-specific fields exist."""
        annotations = getattr(TwinTemplate, "__annotations__", {})
        forbidden = ["protocol", "bacnet_address", "mqtt_topic", "device_id"]
        for field in forbidden:
            assert field not in annotations, f"TwinTemplate must not have {field}"


class TestTemplatePropertyModel:
    """Test TemplateProperty model structure."""

    def test_model_creation(self):
        """Verify TemplateProperty can be instantiated."""
        prop = TemplateProperty(
            id=uuid4(),
            template_id=uuid4(),
            name="temperature",
            data_type="float",
            unit="celsius",
            required=True,
        )
        assert prop.name == "temperature"
        assert prop.data_type == "float"

    def test_table_name(self):
        """Verify table name is template_properties."""
        assert TemplateProperty.__tablename__ == "template_properties"


class TestTemplateRelationshipModel:
    """Test TemplateRelationship model structure."""

    def test_model_creation(self):
        """Verify TemplateRelationship can be instantiated."""
        rel = TemplateRelationship(
            id=uuid4(),
            template_id=uuid4(),
            relationship_type="contains",
            target_template="floor",
        )
        assert rel.relationship_type == "contains"

    def test_table_name(self):
        """Verify table name is template_relationships."""
        assert TemplateRelationship.__tablename__ == "template_relationships"
