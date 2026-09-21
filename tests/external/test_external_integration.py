"""UAA-04 External Integration & Mapping Tests."""
import pytest

from services.iot.src.external.model import (
    ExternalObjectService, EXTERNAL_SYSTEM_CATEGORIES,
    ExternalEvent, ExternalRelationship,
)
from services.iot.src.discovery.engine import DiscoveryEngine
from services.iot.src.classification.engine import ClassificationEngine
from services.iot.src.mapping.generator import MappingGenerator
from services.iot.src.validation.engine import ValidationEngine
from services.iot.src.adapters.mock import BMSMockAdapter, FactoryMockAdapter


# ---------------------------------------------------------------------------
# AC-01: ExternalSystem CRUD with 15 categories
# ---------------------------------------------------------------------------
class TestExternalSystem:
    """AC-01: ExternalSystem CRUD with 15 categories."""

    def test_create_system(self):
        svc = ExternalObjectService()
        system = svc.create_system({
            "id": "sys-bms-01", "code": "bms-building-a", "name": "BMS Building A",
            "category": "BMS", "protocol": "bacnet",
            "connection_config": {"ip": "192.168.1.1", "port": 4780},
        })
        assert system.id == "sys-bms-01"
        assert system.category == "BMS"
        assert system.protocol == "bacnet"

    def test_invalid_category(self):
        svc = ExternalObjectService()
        with pytest.raises(ValueError):
            svc.create_system({
                "id": "sys-bad", "code": "bad", "name": "Bad",
                "category": "InvalidCategory", "protocol": "bacnet",
            })

    def test_list_systems(self):
        svc = ExternalObjectService()
        svc.create_system({"id": "s1", "code": "c1", "name": "N1",
                           "category": "BMS", "protocol": "bacnet"})
        svc.create_system({"id": "s2", "code": "c2", "name": "N2",
                           "category": "SCADA", "protocol": "modbus"})
        systems = svc.list_systems()
        assert len(systems) == 2


# ---------------------------------------------------------------------------
# AC-02: Discovery Engine — BACnet/Modbus/OPC UA
# ---------------------------------------------------------------------------
class TestDiscovery:
    """AC-02: Protocol-specific discovery."""

    def test_discover_bacnet(self):
        engine = DiscoveryEngine()
        results = engine.discover_bacnet()
        assert len(results) >= 2
        assert "bacnet" in results[0].get("address", "")

    def test_discover_modbus(self):
        engine = DiscoveryEngine()
        results = engine.discover_modbus("192.168.1.1")
        assert len(results) >= 2

    def test_discover_opcua(self):
        engine = DiscoveryEngine()
        results = engine.discover_opcua("opc.tcp://localhost:4840")
        assert len(results) >= 2

    def test_discover_unsupported_protocol(self):
        engine = DiscoveryEngine()
        with pytest.raises(ValueError):
            engine.discover("invalid_protocol")


# ---------------------------------------------------------------------------
# AC-03: Classification Engine — Rule-based
# ---------------------------------------------------------------------------
class TestClassification:
    """AC-03: Rule-based classification to Universal types."""

    def test_classify_ahu(self):
        engine = ClassificationEngine()
        result = engine.classify("AHU-001 Supply Air Temp")
        assert result["asset_type"] == "asset.park.hvac.ahu"
        assert result["point_semantic"] == "temperature"

    def test_classify_chiller(self):
        engine = ClassificationEngine()
        result = engine.classify("Chiller-01 Return Water")
        assert result["asset_type"] == "asset.park.facility.chiller"

    def test_classify_cnc(self):
        engine = ClassificationEngine()
        result = engine.classify("CNC Machine 01 Position")
        assert result["asset_type"] == "asset.factory.production.cnc"

    def test_classify_unknown(self):
        engine = ClassificationEngine()
        result = engine.classify("Unknown Device XYZ")
        assert result["asset_type"] == "asset.park.facility.generic"

    def test_classify_batch(self):
        engine = ClassificationEngine()
        objects = [
            {"name": "AHU-001", "type": "Sensor"},
            {"name": "CNC-001", "type": "Machine"},
        ]
        results = engine.classify_batch(objects)
        assert len(results) == 2
        assert results[0]["asset_type"] == "asset.park.hvac.ahu"
        assert results[1]["asset_type"] == "asset.factory.production.cnc"


# ---------------------------------------------------------------------------
# AC-04: Mapping Generator — Discovered → MappingProfile
# ---------------------------------------------------------------------------
class TestMappingGenerator:
    """AC-04: Zero-code MappingProfile generation."""

    def test_generate_bacnet_mapping(self):
        gen = MappingGenerator()
        mapping = gen.generate({
            "object_id": "ai-001", "name": "Temperature",
            "data_type": "float32", "unit": "degC",
        }, "bacnet")
        assert mapping["protocol"] == "bacnet"
        assert "bacnet" in mapping["address"]
        assert mapping["scaling"]["scale"] == 1.0

    def test_generate_modbus_mapping(self):
        gen = MappingGenerator()
        mapping = gen.generate({
            "object_id": "reg-100", "name": "Power",
            "data_type": "int16", "unit": "kW",
        }, "modbus")
        assert mapping["protocol"] == "modbus"
        assert "modbus" in mapping["address"]

    def test_generate_opcua_mapping(self):
        gen = MappingGenerator()
        mapping = gen.generate({
            "object_id": "node-2001", "name": "Pressure",
            "data_type": "float32", "unit": "Pa",
        }, "opcua")
        assert mapping["protocol"] == "opcua"
        assert "opcua" in mapping["address"]

    def test_generate_batch(self):
        gen = MappingGenerator()
        points = [
            {"object_id": "p1", "name": "Temp", "data_type": "float32", "unit": "degC"},
            {"object_id": "p2", "name": "Power", "data_type": "int16", "unit": "kW"},
        ]
        mappings = gen.generate_batch(points, "bacnet")
        assert len(mappings) == 2
        assert all(m["protocol"] == "bacnet" for m in mappings)


# ---------------------------------------------------------------------------
# AC-05: Validation Engine — Round-trip + Quality Scoring
# ---------------------------------------------------------------------------
class TestValidation:
    """AC-05: Round-trip read/write + data quality."""

    def test_round_trip_pass(self):
        engine = ValidationEngine()
        passed, deviation = engine.round_trip_test(25.0, 25.01, tolerance=0.1)
        assert passed is True
        assert deviation < 0.1

    def test_round_trip_fail(self):
        engine = ValidationEngine()
        passed, deviation = engine.round_trip_test(25.0, 30.0, tolerance=0.1)
        assert passed is False
        assert deviation == 5.0

    def test_quality_completeness(self):
        engine = ValidationEngine()
        assert engine.score_completeness(10, 10) == 1.0
        assert engine.score_completeness(10, 5) == 0.5
        assert engine.score_completeness(10, 0) == 0.0

    def test_quality_timeliness(self):
        engine = ValidationEngine()
        assert engine.score_timeliness(0) == 1.0
        assert engine.score_timeliness(30) == 0.5
        assert engine.score_timeliness(120) == 0.0

    def test_quality_validity(self):
        engine = ValidationEngine()
        assert engine.score_validity(50.0, 0.0, 100.0) == 1.0
        assert engine.score_validity(150.0, 0.0, 100.0) < 1.0

    def test_quality_composite(self):
        engine = ValidationEngine()
        score = engine.compute_quality_score(
            value=50.0, min_val=0.0, max_val=100.0,
            age_seconds=10.0, completeness_ratio=1.0,
        )
        assert 0.0 <= score.composite <= 1.0
        assert score.completeness == 1.0
        assert score.validity == 1.0


# ---------------------------------------------------------------------------
# AC-06: BMS Mock — 50+ Building points
# ---------------------------------------------------------------------------
class TestBMSMock:
    """AC-06: BMS Mock with 50+ Building points."""

    def test_bms_point_count(self):
        svc = ExternalObjectService()
        mock = BMSMockAdapter("bms-01", svc)
        count = mock.get_point_count()
        assert count >= 50

    def test_bms_discover(self):
        svc = ExternalObjectService()
        mock = BMSMockAdapter("bms-01", svc)
        points = mock.discover()
        assert len(points) >= 50
        for p in points:
            assert "object_id" in p
            assert "address" in p
            assert "unit" in p

    def test_bms_read_write(self):
        svc = ExternalObjectService()
        mock = BMSMockAdapter("bms-01", svc)
        # Read a point
        result = mock.read_point("temp-ahu-01")
        assert result is not None
        assert result["unit"] == "degC"
        # Write a point
        ok = mock.write_point("temp-ahu-01", 23.5)
        assert ok is True

    def test_bms_register_with_service(self):
        svc = ExternalObjectService()
        mock = BMSMockAdapter("bms-01", svc)
        mock.register_with_service(svc)
        objects = svc.list_by_system("bms-01")
        assert len(objects) >= 50


# ---------------------------------------------------------------------------
# AC-07: Factory Mock — 50+ Production points
# ---------------------------------------------------------------------------
class TestFactoryMock:
    """AC-07: Factory Mock with 50+ Production points."""

    def test_factory_point_count(self):
        svc = ExternalObjectService()
        mock = FactoryMockAdapter("factory-01", svc)
        assert mock.get_point_count() >= 50

    def test_factory_discover(self):
        svc = ExternalObjectService()
        mock = FactoryMockAdapter("factory-01", svc)
        points = mock.discover()
        assert len(points) >= 50
        for p in points:
            assert "object_id" in p

    def test_factory_read_write(self):
        svc = ExternalObjectService()
        mock = FactoryMockAdapter("factory-01", svc)
        result = mock.read_point("plc-vibration-motor-01")
        assert result is not None
        ok = mock.write_point("plc-vibration-motor-01", 3.0)
        assert ok is True

    def test_factory_register_with_service(self):
        svc = ExternalObjectService()
        mock = FactoryMockAdapter("factory-01", svc)
        mock.register_with_service(svc)
        objects = svc.list_by_system("factory-01")
        assert len(objects) >= 50


# ---------------------------------------------------------------------------
# AC-08: Same External Object Model for both mocks
# ---------------------------------------------------------------------------
class TestSharedExternalModel:
    """AC-08: BMS and Factory use identical External Object Model."""

    def test_both_mocks_use_same_service(self):
        """Both mocks register to the same ExternalObjectService."""
        svc = ExternalObjectService()
        bms = BMSMockAdapter("bms-01", svc)
        factory = FactoryMockAdapter("factory-01", svc)

        bms.register_with_service(svc)
        factory.register_with_service(svc)

        bms_objects = svc.list_by_system("bms-01")
        factory_objects = svc.list_by_system("factory-01")

        assert len(bms_objects) >= 50
        assert len(factory_objects) >= 50
        # Different systems, same service, no conflict
        system_ids = {o.system_id for o in bms_objects + factory_objects}
        assert system_ids == {"bms-01", "factory-01"}

    def test_external_event_creation(self):
        svc = ExternalObjectService()
        event = svc.create_event({
            "id": "evt-001", "system_id": "bms-01", "object_id": "temp-ahu-01",
            "event_type": "alarm", "severity": "warning",
            "payload": {"message": "High temperature"},
        })
        assert event.severity == "warning"
        assert event.event_type == "alarm"

    def test_external_event_invalid_severity(self):
        svc = ExternalObjectService()
        with pytest.raises(ValueError):
            svc.create_event({
                "id": "evt-bad", "system_id": "s1", "object_id": "o1",
                "event_type": "test", "severity": "invalid",
            })

    def test_external_relationship(self):
        svc = ExternalObjectService()
        rel = svc.create_relationship({
            "id": "rel-001",
            "source_system_id": "bms-01", "source_object_id": "temp-ahu-01",
            "target_system_id": "factory-01", "target_object_id": "plc-vibration-motor-01",
            "type": "monitors",
        })
        assert rel.type == "monitors"

    def test_external_relationship_invalid_type(self):
        svc = ExternalObjectService()
        with pytest.raises(ValueError):
            svc.create_relationship({
                "id": "rel-bad",
                "source_system_id": "s1", "source_object_id": "o1",
                "target_system_id": "s2", "target_object_id": "o2",
                "type": "invalid_type",
            })
