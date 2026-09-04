"""Test EntityBindingService — Device ↔ TwinEntity binding management."""
import pytest
from uuid import uuid4
from unittest.mock import MagicMock

from services.twin.models import TwinEntity
from services.twin.registry import TwinEntityRegistry
from services.twin.binding import EntityBindingService, BindingRecord
from services.twin.exceptions import TwinBindingError, TwinEntityNotFoundError


class TestEntityBindingService:
    """Tests for EntityBindingService."""

    def setup_method(self):
        """Setup fresh registry and binding service for each test."""
        self.registry = TwinEntityRegistry()
        self.tenant_id = uuid4()

        # Mock device repository
        self.mock_device_repo = MagicMock()
        self.mock_device_repo.get_by_id_for_tenant = MagicMock()

        self.binding_service = EntityBindingService(
            self.registry,
            self.mock_device_repo,
        )

    def _create_entity(self, entity_type: str = "sensor") -> TwinEntity:
        """Helper to create and register a test entity."""
        entity = TwinEntity(
            tenant_id=self.tenant_id,
            name=f"Test {entity_type}",
            entity_type=entity_type,
        )
        return self.registry.register(entity)

    def _setup_device_mock(self, device_id=None, tenant_id=None):
        """Setup mock device repository response."""
        if device_id is None:
            device_id = uuid4()
        if tenant_id is None:
            tenant_id = self.tenant_id

        mock_device = MagicMock()
        mock_device.id = device_id
        mock_device.tenant_id = tenant_id
        mock_device.external_id = "device-001"

        self.mock_device_repo.get_by_id_for_tenant.return_value = mock_device
        return mock_device

    def test_create_binding_success(self):
        """Test successful binding creation."""
        entity = self._create_entity()
        device_id = uuid4()
        self._setup_device_mock(device_id, self.tenant_id)

        binding = self.binding_service.create_binding(
            device_id=device_id,
            entity_id=entity.id,
            tenant_id=self.tenant_id,
            binding_type="mirror",
        )

        assert isinstance(binding, BindingRecord)
        assert binding.device_id == device_id
        assert binding.entity_id == entity.id
        assert binding.tenant_id == self.tenant_id
        assert binding.binding_type == "mirror"

    def test_create_binding_default_type(self):
        """Test binding creation with default type."""
        entity = self._create_entity()
        device_id = uuid4()
        self._setup_device_mock(device_id, self.tenant_id)

        binding = self.binding_service.create_binding(
            device_id=device_id,
            entity_id=entity.id,
            tenant_id=self.tenant_id,
        )

        assert binding.binding_type == "default"

    def test_get_binding(self):
        """Test getting a binding by ID."""
        entity = self._create_entity()
        device_id = uuid4()
        self._setup_device_mock(device_id, self.tenant_id)

        binding = self.binding_service.create_binding(
            device_id=device_id,
            entity_id=entity.id,
            tenant_id=self.tenant_id,
        )

        retrieved = self.binding_service.get_binding(binding.id, self.tenant_id)
        assert retrieved is not None
        assert retrieved.id == binding.id

    def test_get_binding_not_found(self):
        """Test getting non-existent binding returns None."""
        fake_id = uuid4()
        result = self.binding_service.get_binding(fake_id, self.tenant_id)
        assert result is None

    def test_get_binding_by_device(self):
        """Test getting binding by device ID."""
        entity = self._create_entity()
        device_id = uuid4()
        self._setup_device_mock(device_id, self.tenant_id)

        binding = self.binding_service.create_binding(
            device_id=device_id,
            entity_id=entity.id,
            tenant_id=self.tenant_id,
        )

        retrieved = self.binding_service.get_binding_by_device(device_id, self.tenant_id)
        assert retrieved is not None
        assert retrieved.id == binding.id

    def test_remove_binding(self):
        """Test removing a binding."""
        entity = self._create_entity()
        device_id = uuid4()
        self._setup_device_mock(device_id, self.tenant_id)

        binding = self.binding_service.create_binding(
            device_id=device_id,
            entity_id=entity.id,
            tenant_id=self.tenant_id,
        )

        removed = self.binding_service.remove_binding(binding.id, self.tenant_id)
        assert removed is True

        # Verify it's gone
        retrieved = self.binding_service.get_binding(binding.id, self.tenant_id)
        assert retrieved is None

    def test_remove_nonexistent_binding(self):
        """Test removing non-existent binding returns False."""
        fake_id = uuid4()
        removed = self.binding_service.remove_binding(fake_id, self.tenant_id)
        assert removed is False

    def test_list_bindings_pagination(self):
        """Test listing bindings with pagination."""
        entity = self._create_entity()
        device_id = uuid4()
        self._setup_device_mock(device_id, self.tenant_id)

        # Create multiple bindings
        bindings = []
        for i in range(5):
            b = self.binding_service.create_binding(
                device_id=device_id,
                entity_id=entity.id,
                tenant_id=self.tenant_id,
                binding_type=f"type_{i}",
            )
            bindings.append(b)

        # List all
        all_bindings = self.binding_service.list_bindings(self.tenant_id, limit=100)
        assert len(all_bindings) == 5

        # Paginate
        page1 = self.binding_service.list_bindings(self.tenant_id, limit=2, offset=0)
        page2 = self.binding_service.list_bindings(self.tenant_id, limit=2, offset=2)

        assert len(page1) == 2
        assert len(page2) == 2

    def test_count_bindings(self):
        """Test counting bindings."""
        entity = self._create_entity()
        device_id = uuid4()
        self._setup_device_mock(device_id, self.tenant_id)

        # Create 3 bindings
        for i in range(3):
            self.binding_service.create_binding(
                device_id=device_id,
                entity_id=entity.id,
                tenant_id=self.tenant_id,
            )

        count = self.binding_service.count_bindings(self.tenant_id)
        assert count == 3

    def test_device_not_found_raises_error(self):
        """Test that binding creation fails when device not found."""
        entity = self._create_entity()
        fake_device_id = uuid4()

        # Mock device not found
        self.mock_device_repo.get_by_id_for_tenant.return_value = None

        with pytest.raises(TwinBindingError):
            self.binding_service.create_binding(
                device_id=fake_device_id,
                entity_id=entity.id,
                tenant_id=self.tenant_id,
            )

    def test_entity_not_found_raises_error(self):
        """Test that binding creation fails when entity not found."""
        device_id = uuid4()
        self._setup_device_mock(device_id, self.tenant_id)

        fake_entity_id = uuid4()

        with pytest.raises(TwinEntityNotFoundError):
            self.binding_service.create_binding(
                device_id=device_id,
                entity_id=fake_entity_id,
                tenant_id=self.tenant_id,
            )
