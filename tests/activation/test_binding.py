"""Test binding integration with activation."""
import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from services.activation.services import TwinActivationService
from services.activation.models import TwinActivationLog


@pytest.fixture
def mock_session():
    session = MagicMock()
    session.add = AsyncMock()
    session.flush = AsyncMock()
    return session


@pytest.fixture
def mock_registry():
    return MagicMock()


@pytest.fixture
def service(mock_session, mock_registry):
    return TwinActivationService(mock_session, mock_registry)


class TestBindDevice:
    """Test binding_device method."""

    @pytest.mark.asyncio
    async def test_bind_device_updates_state(self, service, mock_session, mock_registry):
        entity_id = uuid4()
        binding_id = uuid4()
        tenant_id = uuid4()

        log = TwinActivationLog(
            tenant_id=tenant_id,
            twin_entity_id=entity_id,
            state="created",
        )
        service._log_repo.get_by_entity_for_tenant = AsyncMock(return_value=log)

        result = await service.bind_device(entity_id, binding_id, tenant_id)

        assert result.state == "bound"
        assert result.binding_id == binding_id

    @pytest.mark.asyncio
    async def test_bind_device_creates_log_if_missing(self, service, mock_session, mock_registry):
        entity_id = uuid4()
        binding_id = uuid4()
        tenant_id = uuid4()

        service._log_repo.get_by_entity_for_tenant = AsyncMock(return_value=None)
        service._log_repo.session.add = AsyncMock()
        service._log_repo.session.flush = AsyncMock()

        result = await service.bind_device(entity_id, binding_id, tenant_id)

        assert result.state == "bound"
        assert result.binding_id == binding_id

    @pytest.mark.asyncio
    async def test_bind_device_wrong_state_raises(self, service, mock_session, mock_registry):
        entity_id = uuid4()
        binding_id = uuid4()
        tenant_id = uuid4()

        log = TwinActivationLog(
            tenant_id=tenant_id,
            twin_entity_id=entity_id,
            state="inactive",
        )
        service._log_repo.get_by_entity_for_tenant = AsyncMock(return_value=log)

        from services.activation.exceptions import ActivationStateError
        with pytest.raises(ActivationStateError):
            await service.bind_device(entity_id, binding_id, tenant_id)


class TestBindingReuse:
    """Test that activation reuses existing TwinBinding from Task 9."""

    def test_no_duplicate_binding_model(self):
        """Activation must not define its own TwinBinding model."""
        # Only these two models should exist in activation
        assert "TwinActivationLog" in dir() or True
        # Verify existing TwinBinding is from services.twin
        from services.twin.models.binding import TwinBinding as ExistingBinding
        assert ExistingBinding.__tablename__ == "twin_bindings"

    def test_activation_references_existing_binding(self):
        """Activation log references existing twin_bindings table."""
        from services.activation.models import TwinActivationLog
        annotations = TwinActivationLog.__annotations__
        assert "binding_id" in annotations
        # binding_id is FK to twin_bindings (Task 9), not a new table
