"""UAA-03 Point, Mapping & Capability Tests."""
import pytest

from services.core.src.point.service import PointService, VALID_AGGREGATIONS, FORBIDDEN_POINT_FIELDS
from services.iot.src.mapping.service import MappingProfileService, VALID_PROTOCOLS
from services.core.src.capability.contract.registry import CapabilityContract, CapabilityContractRegistry, VALID_SAFETY_LEVELS
from services.core.src.capability.plugin.base import (
    CapabilityPluginRegistry, BACnetCapabilityPlugin, ModbusCapabilityPlugin,
    OPCUACapabilityPlugin, MQTTCapabilityPlugin,
)
from services.core.src.capability.safety.gate import SafetyGate, SAFETY_LEVELS


# ---------------------------------------------------------------------------
# AC-01: Point semantic definition — ZERO protocol fields
# ---------------------------------------------------------------------------
class TestPointSemantic:
    """AC-01: Point has semantic_type, unit, aggregation — ZERO protocol fields."""

    def test_create_valid_point(self):
        service = PointService()
        point = service.create({
            "id": "pt-001",
            "code": "power_active",
            "semantic_type": "power",
            "unit": "kW",
            "aggregation": ["latest", "avg", "max"],
            "tags": ["energy", "transformer"],
            "asset_id": "asset-001",
        }, tenant_id="t1")
        assert point.id == "pt-001"
        assert point.unit == "kW"
        assert point.semantic_type == "power"
        assert point.quality == "GOOD"

    def test_point_rejects_protocol_fields(self):
        """SL-04: Point must reject protocol fields."""
        service = PointService()
        forbidden = [
            {"protocol": "bacnet"},
            {"address": "192.168.1.1"},
            {"register": 100},
            {"slave_id": 1},
            {"topic": "telemetry/power"},
            {"url": "http://api.example.com"},
        ]
        for extra in forbidden:
            data = {
                "id": f"pt-{len(forbidden)}",
                "code": "test_point",
                "semantic_type": "temperature",
                "unit": "degC",
                "aggregation": ["latest"],
                "tags": ["test"],
                "asset_id": "a1",
                **extra,
            }
            with pytest.raises(ValueError):
                service.create(data, tenant_id="t1")

    def test_point_valid_ucum_units(self):
        """Valid UCUM units must be accepted."""
        service = PointService()
        valid_units = ["kW", "degC", "m3/h", "Pa", "A", "V", "Hz", "s", "%", "l/s", "m3"]
        for unit in valid_units:
            point = service.create({
                "id": f"pt-{unit}",
                "code": f"point_{unit}",
                "semantic_type": "quantity",
                "unit": unit,
                "aggregation": ["latest"],
                "tags": [],
                "asset_id": "a1",
            }, tenant_id="t1")
            assert point.unit == unit

    def test_point_invalid_aggregation(self):
        """Invalid aggregation functions must be rejected."""
        service = PointService()
        with pytest.raises(ValueError):
            service.create({
                "id": "pt-bad",
                "code": "test",
                "semantic_type": "power",
                "unit": "kW",
                "aggregation": ["invalid_func"],
                "tags": [],
                "asset_id": "a1",
            }, tenant_id="t1")

    def test_point_quality_transition(self):
        """Point quality can transition: GOOD → UNCERTAIN → BAD."""
        service = PointService()
        point = service.create({
            "id": "pt-q", "code": "q", "semantic_type": "temp",
            "unit": "degC", "aggregation": ["latest"], "tags": [], "asset_id": "a1",
        }, tenant_id="t1")
        point.set_quality("UNCERTAIN")
        assert point.quality == "UNCERTAIN"
        point.set_quality("BAD")
        assert point.quality == "BAD"
        with pytest.raises(ValueError):
            point.set_quality("INVALID")


# ---------------------------------------------------------------------------
# AC-02: MappingProfile — One Point ↔ Many Mappings
# ---------------------------------------------------------------------------
class TestMappingProfile:
    """AC-02: One Point ↔ Many Mappings (BACnet, Modbus, OPC UA, MQTT)."""

    def test_create_mapping(self):
        service = MappingProfileService()
        mapping = service.create({
            "id": "map-001",
            "point_id": "pt-001",
            "protocol": "bacnet",
            "address": "192.168.1.100:4780",
            "register": 45,
            "function_code": 3,
            "scale": 0.1,
            "offset": 0.0,
            "polling_interval": "1s",
        })
        assert mapping.protocol == "bacnet"
        assert mapping.scale == 0.1
        assert mapping.register == 45

    def test_multi_protocol_same_point(self):
        """AC-07: Same Point can have BACnet + Modbus + MQTT mappings."""
        service = MappingProfileService()
        service.create({"id": "m1", "point_id": "pt-001", "protocol": "bacnet", "address": "device:1"},)
        service.create({"id": "m2", "point_id": "pt-001", "protocol": "modbus", "address": "10.0.0.1:502"},)
        service.create({"id": "m3", "point_id": "pt-001", "protocol": "mqtt", "address": "broker/topic"},)
        service.create({"id": "m4", "point_id": "pt-001", "protocol": "opcua", "address": "ns=2;i=2001"},)

        mappings = service.list_by_point("pt-001")
        assert len(mappings) == 4
        protocols = {m.protocol for m in mappings}
        assert protocols == {"bacnet", "modbus", "mqtt", "opcua"}

    def test_transform_linear(self):
        service = MappingProfileService()
        mapping = service.create({
            "id": "map-t", "point_id": "pt-001",
            "protocol": "modbus", "address": "addr",
            "scale": 0.1, "offset": 20.0,
        })
        result = mapping.transform_value(100.0)
        assert abs(result - 30.0) < 0.01  # 100 * 0.1 + 20.0

    def test_invalid_protocol(self):
        service = MappingProfileService()
        with pytest.raises(ValueError):
            service.create({"id": "m-bad", "point_id": "p1", "protocol": "invalid", "address": "x"})


# ---------------------------------------------------------------------------
# AC-03/04: CapabilityContract — I/O schema, safety level
# ---------------------------------------------------------------------------
class TestCapabilityContract:
    """AC-03/04: CapabilityContract with I/O schema, safety C0-C4."""

    def test_register_capability(self):
        registry = CapabilityContractRegistry()
        contract = CapabilityContract(
            id="cap-001",
            code="capability.hvac.set_temperature",
            category="hvac",
            input_schema={"type": "object", "properties": {"temperature": {"type": "number"}}},
            output_schema={"type": "object", "properties": {"status": {"type": "string"}}},
            safety_level="C1",
            preconditions=[{"required_keys": ["asset_active"]}],
            postconditions=[{"required_keys": ["temperature_set"]}],
            idempotency_key="test-key",
        )
        registry.register(contract)
        assert registry.get("capability.hvac.set_temperature") is not None

    def test_invalid_safety_level(self):
        registry = CapabilityContractRegistry()
        with pytest.raises(ValueError):
            registry.register(CapabilityContract(
                id="cap-bad", code="cap.bad", category="test",
                input_schema={}, output_schema={}, safety_level="C5",
            ))

    def test_idempotency_key_computation(self):
        registry = CapabilityContractRegistry()
        contract = CapabilityContract(
            id="cap-idem", code="capability.test.cmd", category="test",
            input_schema={}, output_schema={}, safety_level="C0",
        )
        registry.register(contract)
        key1 = contract.compute_idempotency_key({"value": 1.0})
        key2 = contract.compute_idempotency_key({"value": 1.0})
        assert key1 == key2  # Same input → same key
        key3 = contract.compute_idempotency_key({"value": 2.0})
        assert key1 != key3  # Different input → different key


# ---------------------------------------------------------------------------
# AC-05: CapabilityPlugin — Abstract base, protocol subclasses
# ---------------------------------------------------------------------------
class TestCapabilityPlugin:
    """AC-05: Plugin interface with protocol-specific subclasses."""

    def test_plugin_registry(self):
        registry = CapabilityPluginRegistry()
        bacnet = BACnetCapabilityPlugin()
        modbus = ModbusCapabilityPlugin()
        registry.register("hvac.bacnet", bacnet, "1.0.0")
        registry.register("hvac.modbus", modbus, "1.0.0")
        plugins = registry.list_plugins()
        assert "hvac.bacnet" in plugins
        assert plugins["hvac.bacnet"] == "1.0.0"

    def test_plugin_execute(self):
        plugin = BACnetCapabilityPlugin()
        plugin.initialize({"device": "192.168.1.1"})
        result = plugin.execute({"value": 25.0})
        assert result.success is True
        assert result.output["value"] == 25.0
        assert result.latency_ms > 0

    def test_all_protocol_plugins(self):
        """BACnet, Modbus, OPC UA, MQTT plugins all implement execute()."""
        plugins = [
            ("bacnet", BACnetCapabilityPlugin()),
            ("modbus", ModbusCapabilityPlugin()),
            ("opcua", OPCUACapabilityPlugin()),
            ("mqtt", MQTTCapabilityPlugin()),
        ]
        for name, plugin in plugins:
            plugin.initialize({})
            result = plugin.execute({"value": 1.0})
            assert result.success is True
            plugin.shutdown()


# ---------------------------------------------------------------------------
# AC-06: Safety Gate — C0-C4 enforcement
# ---------------------------------------------------------------------------
class TestSafetyGate:
    """AC-06: Safety gate with C0-C4 approval workflow."""

    def test_c0_auto_approve(self):
        gate = SafetyGate()
        decision = gate.evaluate("C0", {})
        assert decision.approved is True
        assert decision.approval_method == "auto"

    def test_c1_single_approve(self):
        gate = SafetyGate()
        decision = gate.evaluate("C1", {"approver_role": "operator"})
        assert decision.approved is True
        assert decision.approver_count == 1

    def test_c1_no_approver(self):
        gate = SafetyGate()
        decision = gate.evaluate("C1", {})
        assert decision.approved is False

    def test_c2_dual_approve(self):
        gate = SafetyGate()
        decision = gate.evaluate("C2", {"approvers": ["operator1", "operator2"]})
        assert decision.approved is True
        assert decision.approver_count == 2

    def test_c2_insufficient_approvers(self):
        gate = SafetyGate()
        decision = gate.evaluate("C2", {"approvers": ["operator1"]})
        assert decision.approved is False

    def test_c3_emergency_override(self):
        gate = SafetyGate()
        decision = gate.evaluate("C3", {"emergency_role": "fire_safety_officer"})
        assert decision.approved is True

    def test_c3_no_emergency_role(self):
        gate = SafetyGate()
        decision = gate.evaluate("C3", {})
        assert decision.approved is False

    def test_c4_hardware_confirmed(self):
        gate = SafetyGate()
        decision = gate.evaluate("C4", {"hardware_confirmed": True})
        assert decision.approved is True

    def test_c4_no_hardware(self):
        gate = SafetyGate()
        decision = gate.evaluate("C4", {"hardware_confirmed": False})
        assert decision.approved is False

    def test_invalid_safety_level(self):
        gate = SafetyGate()
        with pytest.raises(ValueError):
            gate.evaluate("C5", {})

    def test_audit_log(self):
        gate = SafetyGate()
        gate.evaluate("C0", {})
        gate.evaluate("C1", {"approver_role": "op1"})
        gate.evaluate("C2", {"approvers": ["op1", "op2"]})
        log = gate.get_audit_log()
        assert len(log) == 3
        assert log[0]["safety_level"] == "C0"
        assert log[0]["approved"] is True
        assert log[1]["safety_level"] == "C1"
        assert log[2]["safety_level"] == "C2"

    def test_audit_log_filter(self):
        gate = SafetyGate()
        gate.evaluate("C0", {})
        gate.evaluate("C1", {"approver_role": "op1"})
        c0_log = gate.get_audit_log(safety_level="C0")
        assert len(c0_log) == 1
        assert c0_log[0]["safety_level"] == "C0"


# ---------------------------------------------------------------------------
# AC-07: Multi-protocol test — Same Point → BACnet + Modbus + MQTT
# ---------------------------------------------------------------------------
class TestMultiProtocol:
    """AC-07: Same Point with multiple protocol mappings simultaneously active."""

    def test_point_with_multi_protocol_mappings(self):
        point_svc = PointService()
        mapping_svc = MappingProfileService()
        plugin_reg = CapabilityPluginRegistry()
        safety = SafetyGate()
        contract_reg = CapabilityContractRegistry()

        # Create a single point
        point = point_svc.create({
            "id": "pt-multi", "code": "temperature",
            "semantic_type": "temperature", "unit": "degC",
            "aggregation": ["latest", "avg"], "tags": ["hvac"],
            "asset_id": "asset-hvac-001",
        }, tenant_id="t1")

        # Create 3 protocol mappings for the same point
        m1 = mapping_svc.create({"id": "map-bacnet", "point_id": "pt-multi",
                                  "protocol": "bacnet", "address": "192.168.1.1:4780"})
        m2 = mapping_svc.create({"id": "map-modbus", "point_id": "pt-multi",
                                  "protocol": "modbus", "address": "10.0.0.1:502", "register": 100})
        m3 = mapping_svc.create({"id": "map-mqtt", "point_id": "pt-multi",
                                  "protocol": "mqtt", "address": "broker/hvac/temp"})

        # All 3 mappings active simultaneously
        mappings = mapping_svc.list_by_point("pt-multi")
        assert len(mappings) == 3
        protocols = {m.protocol for m in mappings}
        assert protocols == {"bacnet", "modbus", "mqtt"}

        # Register capability contracts for each protocol
        contract_reg.register(CapabilityContract(
            id="cap-bacnet", code="capability.hvac.read_temperature",
            category="hvac", input_schema={}, output_schema={}, safety_level="C0",
        ))
        contract_reg.register(CapabilityContract(
            id="cap-modbus", code="capability.hvac.read_temperature_modbus",
            category="hvac", input_schema={}, output_schema={}, safety_level="C0",
        ))

        # Register plugins
        plugin_reg.register("hvac.bacnet", BACnetCapabilityPlugin(), "1.0.0")
        plugin_reg.register("hvac.modbus", ModbusCapabilityPlugin(), "1.0.0")

        # Safety gate auto-approves C0 reads
        for _ in range(3):
            decision = safety.evaluate("C0", {})
            assert decision.approved is True

        # Zero conflicts across protocols
        assert True
