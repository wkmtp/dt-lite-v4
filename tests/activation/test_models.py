"""Test activation models."""


class TestTwinActivationLogModel:
    """Test TwinActivationLog model structure."""

    def test_table_name(self):
        from services.activation.models import TwinActivationLog
        assert TwinActivationLog.__tablename__ == "twin_activation_logs"

    def test_has_tenant_id(self):
        from services.activation.models import TwinActivationLog
        annotations = TwinActivationLog.__annotations__
        assert "tenant_id" in annotations

    def test_has_twin_entity_id(self):
        from services.activation.models import TwinActivationLog
        annotations = TwinActivationLog.__annotations__
        assert "twin_entity_id" in annotations

    def test_has_state_field(self):
        from services.activation.models import TwinActivationLog
        annotations = TwinActivationLog.__annotations__
        assert "state" in annotations

    def test_has_binding_id(self):
        from services.activation.models import TwinActivationLog
        annotations = TwinActivationLog.__annotations__
        assert "binding_id" in annotations

    def test_no_device_fields(self):
        """Activation log must not have device-specific fields."""
        from services.activation.models import TwinActivationLog
        annotations = TwinActivationLog.__annotations__
        for field in ["device_id", "protocol", "endpoint", "bacnet_address"]:
            assert field not in annotations, f"Forbidden field: {field}"

    def test_no_telemetry_fields(self):
        """Activation log must not have telemetry fields."""
        from services.activation.models import TwinActivationLog
        annotations = TwinActivationLog.__annotations__
        for field in ["telemetry_value", "datapoint_id", "raw_value"]:
            assert field not in annotations

    def test_state_values_allowed(self):
        from services.activation.activation import get_activation_states
        allowed = set(get_activation_states())
        assert allowed == {"created", "bound", "active", "inactive", "error"}


class TestTwinCommandModel:
    """Test TwinCommand model structure."""

    def test_table_name(self):
        from services.activation.models import TwinCommand
        assert TwinCommand.__tablename__ == "twin_commands"

    def test_has_tenant_id(self):
        from services.activation.models import TwinCommand
        annotations = TwinCommand.__annotations__
        assert "tenant_id" in annotations

    def test_has_binding_id(self):
        from services.activation.models import TwinCommand
        annotations = TwinCommand.__annotations__
        assert "twin_binding_id" in annotations

    def test_has_command_type(self):
        from services.activation.models import TwinCommand
        annotations = TwinCommand.__annotations__
        assert "command_type" in annotations

    def test_has_payload(self):
        from services.activation.models import TwinCommand
        annotations = TwinCommand.__annotations__
        assert "payload" in annotations

    def test_has_status(self):
        from services.activation.models import TwinCommand
        annotations = TwinCommand.__annotations__
        assert "status" in annotations

    def test_no_protocol_fields(self):
        from services.activation.models import TwinCommand
        annotations = TwinCommand.__annotations__
        for field in ["protocol", "bacnet", "modbus", "mqtt_topic"]:
            assert field not in annotations
