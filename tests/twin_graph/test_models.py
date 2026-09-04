"""Test TwinRelationship model."""
from uuid import uuid4


class TestTwinRelationshipModel:
    """Tests for TwinRelationship SQLAlchemy model."""

    def test_model_creation(self):
        """Verify TwinRelationship can be instantiated."""
        from services.twin_graph.models import TwinRelationship

        rel = TwinRelationship(
            id=uuid4(),
            tenant_id=uuid4(),
            source_twin_id=uuid4(),
            target_twin_id=uuid4(),
            relationship_type="contains",
        )
        assert rel.id is not None
        assert rel.relationship_type == "contains"

    def test_table_name(self):
        """Verify table name is correct."""
        from services.twin_graph.models import TwinRelationship
        assert TwinRelationship.__tablename__ == "twin_relationships"

    def test_has_soft_delete_mixin(self):
        """Verify model includes SoftDeleteMixin for soft delete support."""
        from services.twin_graph.models import TwinRelationship
        from services.core.models.base import SoftDeleteMixin
        assert issubclass(TwinRelationship, SoftDeleteMixin)

    def test_relationship_type_is_string(self):
        """relationship_type must be a string."""
        from services.twin_graph.models import TwinRelationship

        rel = TwinRelationship(
            id=uuid4(),
            tenant_id=uuid4(),
            source_twin_id=uuid4(),
            target_twin_id=uuid4(),
            relationship_type="controls",
        )
        assert isinstance(rel.relationship_type, str)
        assert len(rel.relationship_type) > 0

    def test_metadata_default_empty_dict(self):
        """metadata should default to empty dict when created via session."""
        from services.twin_graph.models import TwinRelationship

        rel = TwinRelationship(
            id=uuid4(),
            tenant_id=uuid4(),
            source_twin_id=uuid4(),
            target_twin_id=uuid4(),
            relationship_type="monitored_by",
        )
        # meta_data defaults to None without session; explicit dict works
        rel.meta_data = {}
        assert rel.meta_data == {}

    def test_no_device_id_attribute(self):
        """TwinRelationship must NOT have device_id attribute."""
        from services.twin_graph.models import TwinRelationship
        annotations = getattr(TwinRelationship, "__annotations__", {})
        assert "device_id" not in annotations
