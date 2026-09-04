"""Test deployment models."""
from services.deployment.models import (
    DeploymentInstance,
    DeploymentNode,
    DeploymentNodeCapability,
    DeploymentProfile,
)


class TestDeploymentProfileModel:
    """Test DeploymentProfile model structure."""

    def test_table_name(self):
        assert DeploymentProfile.__tablename__ == "deployment_profiles"

    def test_has_soft_delete(self):
        assert hasattr(DeploymentProfile, 'deleted_at')

    def test_unique_constraint_tenant_name(self):
        table = DeploymentProfile.__table__
        unique_constraints = [c.name for c in table.constraints if hasattr(c, "name")]
        assert "uq_profile_tenant_name" in unique_constraints

    def test_no_device_fields(self):
        annotations = DeploymentProfile.__annotations__
        forbidden = ["device_id", "protocol", "sensor_data"]
        for field in forbidden:
            assert field not in annotations

    def test_has_industry_field(self):
        assert "industry" in DeploymentProfile.__annotations__

    def test_has_template_fk(self):
        cols = [c.name for c in DeploymentProfile.__table__.columns]
        assert "template_id" in cols


class TestDeploymentInstanceModel:
    """Test DeploymentInstance model structure."""

    def test_table_name(self):
        assert DeploymentInstance.__tablename__ == "deployment_instances"

    def test_has_lifecycle_status_column(self):
        cols = [c.name for c in DeploymentInstance.__table__.columns]
        assert "status" in cols

    def test_check_constraint_status(self):
        table = DeploymentInstance.__table__
        assert any('ck_instance_status' in str(c) for c in table.constraints)

    def test_no_runtime_fields(self):
        annotations = DeploymentInstance.__annotations__
        forbidden = ["runtime_state", "current_value", "sensor_data"]
        for field in forbidden:
            assert field not in annotations

    def test_has_profile_fk(self):
        cols = [c.name for c in DeploymentInstance.__table__.columns]
        assert "profile_id" in cols


class TestDeploymentNodeModel:
    """Test DeploymentNode model structure."""

    def test_table_name(self):
        assert DeploymentNode.__tablename__ == "deployment_nodes"

    def test_no_device_or_protocol_fields(self):
        annotations = DeploymentNode.__annotations__
        forbidden = ["device_id", "protocol", "bacnet_address", "modbus_addr"]
        for field in forbidden:
            assert field not in annotations

    def test_has_node_type(self):
        assert "node_type" in DeploymentNode.__annotations__

    def test_has_entity_type_fk(self):
        cols = [c.name for c in DeploymentNode.__table__.columns]
        assert "entity_type_id" in cols

    def test_has_deployment_fk(self):
        cols = [c.name for c in DeploymentNode.__table__.columns]
        assert "deployment_id" in cols


class TestDeploymentNodeCapabilityModel:
    """Test DeploymentNodeCapability model structure."""

    def test_table_name(self):
        assert DeploymentNodeCapability.__tablename__ == "deployment_node_capabilities"

    def test_has_configuration_schema(self):
        assert "configuration_schema" in DeploymentNodeCapability.__annotations__

    def test_has_required_field(self):
        assert "required" in DeploymentNodeCapability.__annotations__

    def test_no_protocol_fields(self):
        annotations = DeploymentNodeCapability.__annotations__
        forbidden = ["protocol", "bacnet", "modbus", "mqtt_topic", "opcua_nodeid"]
        for field in forbidden:
            assert field not in annotations

    def test_unique_node_capability(self):
        table = DeploymentNodeCapability.__table__
        unique_constraints = [c.name for c in table.constraints if hasattr(c, "name")]
        assert "uq_node_capability" in unique_constraints
