"""Test provisioning models."""
from services.provisioning.models import (
    ProvisioningExecution,
    ProvisioningItem,
    ProvisioningPlan,
)


class TestProvisioningPlanModel:
    """Test ProvisioningPlan model structure."""

    def test_table_name(self):
        assert ProvisioningPlan.__tablename__ == "provisioning_plans"

    def test_has_soft_delete(self):
        assert hasattr(ProvisioningPlan, 'deleted_at')

    def test_unique_constraint_tenant_deployment(self):
        table = ProvisioningPlan.__table__
        unique_constraints = [c.name for c in table.constraints if hasattr(c, "name")]
        assert "uq_plan_deployment" in unique_constraints

    def test_no_device_fields(self):
        annotations = ProvisioningPlan.__annotations__
        forbidden = ["device_id", "protocol", "sensor_data"]
        for field in forbidden:
            assert field not in annotations

    def test_has_deployment_fk(self):
        cols = [c.name for c in ProvisioningPlan.__table__.columns]
        assert "deployment_instance_id" in cols

    def test_has_status_field(self):
        assert "status" in ProvisioningPlan.__annotations__


class TestProvisioningItemModel:
    """Test ProvisioningItem model structure."""

    def test_table_name(self):
        assert ProvisioningItem.__tablename__ == "provisioning_items"

    def test_no_protocol_fields(self):
        annotations = ProvisioningItem.__annotations__
        forbidden = ["protocol", "bacnet", "modbus", "mqtt_topic", "opcua_nodeid"]
        for field in forbidden:
            assert field not in annotations

    def test_has_action_field(self):
        assert "action" in ProvisioningItem.__annotations__

    def test_has_external_id_field(self):
        assert "external_id" in ProvisioningItem.__annotations__

    def test_has_twin_fk(self):
        cols = [c.name for c in ProvisioningItem.__table__.columns]
        assert "source_twin_id" in cols
        assert "target_twin_id" in cols
        assert "created_twin_id" in cols

    def test_has_rel_type_field(self):
        assert "rel_type" in ProvisioningItem.__annotations__


class TestProvisioningExecutionModel:
    """Test ProvisioningExecution model structure."""

    def test_table_name(self):
        assert ProvisioningExecution.__tablename__ == "provisioning_executions"

    def test_has_started_at(self):
        assert "started_at" in ProvisioningExecution.__annotations__

    def test_has_finished_at(self):
        assert "finished_at" in ProvisioningExecution.__annotations__

    def test_has_error_message(self):
        assert "error_message" in ProvisioningExecution.__annotations__

    def test_has_item_counts(self):
        annotations = ProvisioningExecution.__annotations__
        assert "items_completed" in annotations
        assert "items_failed" in annotations

    def test_no_device_or_runtime_fields(self):
        annotations = ProvisioningExecution.__annotations__
        forbidden = ["device_id", "runtime_state", "telemetry_value"]
        for field in forbidden:
            assert field not in annotations
