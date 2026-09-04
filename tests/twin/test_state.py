"""Test TwinStateManager — Runtime state management."""
import pytest
from uuid import uuid4
from datetime import datetime, timezone

from services.iota.contracts import NormalizedTelemetry
from services.twin.models import TwinEntity
from services.twin.registry import TwinEntityRegistry
from services.twin.state import TwinStateManager
from services.twin.exceptions import TwinEntityNotFoundError


class TestTwinStateManager:
    """Tests for TwinStateManager."""

    def setup_method(self):
        """Setup fresh registry and state manager for each test."""
        self.registry = TwinEntityRegistry()
        self.state_manager = TwinStateManager(self.registry)
        self.tenant_id = uuid4()

    def _create_entity(self, entity_type: str = "sensor") -> TwinEntity:
        """Helper to create and register a test entity."""
        entity = TwinEntity(
            tenant_id=self.tenant_id,
            name=f"Test {entity_type}",
            entity_type=entity_type,
        )
        return self.registry.register(entity)

    def _create_telemetry(self, value, data_type: str = "FLOAT", quality: str = "GOOD"):
        """Helper to create test telemetry."""
        return NormalizedTelemetry(
            tenant_id=str(self.tenant_id),
            device_id=str(uuid4()),
            datapoint_id=str(uuid4()),
            event_time=datetime.now(timezone.utc),
            ingested_at=datetime.now(timezone.utc),
            value=value,
            data_type=data_type,
            unit="degC",
            quality=quality,
        )

    def test_update_state_from_telemetry(self):
        """Test updating state from telemetry event."""
        entity = self._create_entity()
        telemetry = self._create_telemetry(value=25.5)

        result = self.state_manager.update_state(entity.id, telemetry, self.tenant_id)

        assert result["value"] == 25.5
        assert result["data_type"] == "FLOAT"
        assert result["quality"] == "GOOD"
        assert "event_time" in result
        assert "unit" in result

    def test_get_state_returns_dict(self):
        """Test getting state returns a dictionary."""
        entity = self._create_entity()
        telemetry = self._create_telemetry(value=30.0)
        self.state_manager.update_state(entity.id, telemetry, self.tenant_id)

        state = self.state_manager.get_state(entity.id, self.tenant_id)

        assert isinstance(state, dict)
        assert state["value"] == 30.0

    def test_get_state_nonexistent_entity(self):
        """Test getting state for non-existent entity returns None."""
        fake_id = uuid4()
        result = self.state_manager.get_state(fake_id, self.tenant_id)
        assert result is None

    def test_update_state_nonexistent_entity_raises(self):
        """Test updating state for non-existent entity raises error."""
        fake_id = uuid4()
        telemetry = self._create_telemetry(value=25.0)

        with pytest.raises(TwinEntityNotFoundError):
            self.state_manager.update_state(fake_id, telemetry, self.tenant_id)

    def test_clear_state(self):
        """Test clearing state removes all values."""
        entity = self._create_entity()
        telemetry = self._create_telemetry(value=25.0)
        self.state_manager.update_state(entity.id, telemetry, self.tenant_id)

        cleared = self.state_manager.clear_state(entity.id, self.tenant_id)
        assert cleared is True

        state = self.state_manager.get_state(entity.id, self.tenant_id)
        assert state == {}

    def test_clear_nonexistent_entity(self):
        """Test clearing state for non-existent entity returns False."""
        fake_id = uuid4()
        cleared = self.state_manager.clear_state(fake_id, self.tenant_id)
        assert cleared is False

    def test_list_states_pagination(self):
        """Test listing states with pagination."""
        # Create multiple entities with states
        for i in range(5):
            entity = self._create_entity(f"type_{i}")
            telemetry = self._create_telemetry(value=float(i))
            self.state_manager.update_state(entity.id, telemetry, self.tenant_id)

        all_states = self.state_manager.list_states(self.tenant_id, limit=100)
        assert len(all_states) == 5

        # Paginate
        page1 = self.state_manager.list_states(self.tenant_id, limit=2, offset=0)
        page2 = self.state_manager.list_states(self.tenant_id, limit=2, offset=2)

        assert len(page1) == 2
        assert len(page2) == 2

    def test_state_persistence_across_updates(self):
        """Test that state persists across multiple updates."""
        entity = self._create_entity()

        # First update
        telemetry1 = self._create_telemetry(value=25.0)
        self.state_manager.update_state(entity.id, telemetry1, self.tenant_id)

        # Second update
        telemetry2 = self._create_telemetry(value=30.0)
        self.state_manager.update_state(entity.id, telemetry2, self.tenant_id)

        # State should have both values merged
        state = self.state_manager.get_state(entity.id, self.tenant_id)
        assert state["value"] == 30.0

    def test_state_with_different_data_types(self):
        """Test state updates with different data types."""
        entity = self._create_entity()

        # Float value
        telemetry_float = self._create_telemetry(value=25.5, data_type="FLOAT")
        self.state_manager.update_state(entity.id, telemetry_float, self.tenant_id)

        # Integer value
        telemetry_int = self._create_telemetry(value=42, data_type="INTEGER")
        self.state_manager.update_state(entity.id, telemetry_int, self.tenant_id)

        # Boolean value
        telemetry_bool = self._create_telemetry(value=True, data_type="BOOLEAN")
        self.state_manager.update_state(entity.id, telemetry_bool, self.tenant_id)

        state = self.state_manager.get_state(entity.id, self.tenant_id)
        assert state["value"] is True
        assert state["data_type"] == "BOOLEAN"

    def test_timestamps_are_utc(self):
        """Test that timestamps are stored as UTC."""
        entity = self._create_entity()
        telemetry = self._create_telemetry(value=25.0)

        self.state_manager.update_state(entity.id, telemetry, self.tenant_id)

        state = self.state_manager.get_state(entity.id, self.tenant_id)
        assert state["event_time"] is not None
        assert "T" in state["event_time"]  # ISO format
