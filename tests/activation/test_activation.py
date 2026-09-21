"""Test activation service."""
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
    session.execute = AsyncMock()
    return session


@pytest.fixture
def mock_registry():
    return MagicMock()


@pytest.fixture
def service(mock_session, mock_registry):
    return TwinActivationService(mock_session, mock_registry)


class TestActivateEntity:
    """Test activation service activate method."""

    @pytest.mark.asyncio
    async def test_activate_creates_registry_entry(self, service, mock_session, mock_registry):
        entity_id = uuid4()
        tenant_id = uuid4()

        # Mock entity
        mock_entity = MagicMock()
        mock_entity.id = entity_id
        mock_entity.tenant_id = tenant_id
        mock_entity.name = "Test Entity"
        mock_entity.definition_id = uuid4()
        service._entity_repo.get_by_id_for_tenant = AsyncMock(return_value=mock_entity)

        # Mock definition
        mock_definition = MagicMock()
        mock_definition.code = "hvac_unit"
        service._definition_repo.get_by_id_for_tenant = AsyncMock(return_value=mock_definition)

        # Mock activation log (not yet created)
        service._log_repo.get_by_entity_for_tenant = AsyncMock(return_value=None)
        service._log_repo.session.add = AsyncMock()
        service._log_repo.session.flush = AsyncMock()

        # Register should be called
        mock_registry.register = MagicMock()

        result = await service.activate(entity_id, tenant_id)

        assert result.state == "active"
        assert result.activated_at is not None
        mock_registry.register.assert_called_once()

    @pytest.mark.asyncio
    async def test_activate_entity_not_found(self, service, mock_session, mock_registry):
        entity_id = uuid4()
        tenant_id = uuid4()

        service._entity_repo.get_by_id_for_tenant = AsyncMock(return_value=None)

        with pytest.raises(Exception):
            await service.activate(entity_id, tenant_id)


class TestDeactivateEntity:
    """Test activation service deactivate method."""

    @pytest.mark.asyncio
    async def test_deactivate_removes_from_registry(self, service, mock_session, mock_registry):
        entity_id = uuid4()
        tenant_id = uuid4()

        # Mock entity
        mock_entity = MagicMock()
        mock_entity.id = entity_id
        mock_entity.tenant_id = tenant_id
        service._entity_repo.get_by_id_for_tenant = AsyncMock(return_value=mock_entity)

        # Mock existing log
        log = TwinActivationLog(
            tenant_id=tenant_id,
            twin_entity_id=entity_id,
            state="active",
            activated_at=MagicMock(),
        )
        service._log_repo.get_by_entity_for_tenant = AsyncMock(return_value=log)

        mock_registry.remove = MagicMock()

        result = await service.deactivate(entity_id, tenant_id)

        assert result.state == "inactive"
        assert result.deactivated_at is not None
        mock_registry.remove.assert_called_once()

    @pytest.mark.asyncio
    async def test_deactivate_already_inactive(self, service, mock_session, mock_registry):
        entity_id = uuid4()
        tenant_id = uuid4()

        mock_entity = MagicMock()
        mock_entity.id = entity_id
        mock_entity.tenant_id = tenant_id
        service._entity_repo.get_by_id_for_tenant = AsyncMock(return_value=mock_entity)

        log = TwinActivationLog(
            tenant_id=tenant_id,
            twin_entity_id=entity_id,
            state="inactive",
        )
        service._log_repo.get_by_entity_for_tenant = AsyncMock(return_value=log)

        from services.activation.exceptions import ActivationAlreadyInactiveError
        with pytest.raises(ActivationAlreadyInactiveError):
            await service.deactivate(entity_id, tenant_id)


class TestGetStatus:
    """Test activation service get_status method."""

    @pytest.mark.asyncio
    async def test_get_status_existing(self, service, mock_session, mock_registry):
        entity_id = uuid4()
        tenant_id = uuid4()

        log = TwinActivationLog(
            tenant_id=tenant_id,
            twin_entity_id=entity_id,
            state="active",
        )
        service._log_repo.get_by_entity_for_tenant = AsyncMock(return_value=log)

        result = await service.get_status(entity_id, tenant_id)
        assert result.state == "active"

    @pytest.mark.asyncio
    async def test_get_status_creates_if_missing(self, service, mock_session, mock_registry):
        entity_id = uuid4()
        tenant_id = uuid4()

        service._log_repo.get_by_entity_for_tenant = AsyncMock(return_value=None)
        service._log_repo.session.add = AsyncMock()
        service._log_repo.session.flush = AsyncMock()

        result = await service.get_status(entity_id, tenant_id)
        assert result.state == "created"
