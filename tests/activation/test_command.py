"""Test command service."""
import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from services.activation.command import TwinCommandService
from services.activation.models import TwinCommand


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
def command_service(mock_session, mock_registry):
    return TwinCommandService(mock_session, mock_registry)


class TestCreateCommand:
    """Test command creation."""

    @pytest.mark.asyncio
    async def test_create_command_success(self, command_service, mock_session, mock_registry):
        binding_id = uuid4()
        device_id = uuid4()
        tenant_id = uuid4()

        # Mock binding
        mock_binding = MagicMock()
        mock_binding.id = binding_id
        mock_binding.twin_entity_id = uuid4()
        command_service._binding_repo.get_by_id_for_tenant = AsyncMock(return_value=mock_binding)

        # Mock activation log
        command_service._activation_service.get_status = AsyncMock(
            return_value=MagicMock(state="active")
        )

        command_service._command_repo.create = AsyncMock(return_value=TwinCommand(
            tenant_id=tenant_id,
            twin_binding_id=binding_id,
            target_device_id=device_id,
            command_type="write",
            payload={},
            status="created",
        ))

        result = await command_service.create_command(
            binding_id=binding_id,
            target_device_id=device_id,
            command_type="write",
            payload={"setpoint": 22.5},
            tenant_id=tenant_id,
        )

        assert result.status == "created"
        assert result.command_type == "write"

    @pytest.mark.asyncio
    async def test_create_command_binding_not_active(self, command_service, mock_session, mock_registry):
        binding_id = uuid4()
        device_id = uuid4()
        tenant_id = uuid4()

        mock_binding = MagicMock()
        mock_binding.id = binding_id
        mock_binding.twin_entity_id = uuid4()
        command_service._binding_repo.get_by_id_for_tenant = AsyncMock(return_value=mock_binding)

        command_service._activation_service.get_status = AsyncMock(
            return_value=MagicMock(state="inactive")
        )

        from services.activation.exceptions import BindingNotActiveError
        with pytest.raises(BindingNotActiveError):
            await command_service.create_command(
                binding_id=binding_id,
                target_device_id=device_id,
                command_type="write",
                payload={},
                tenant_id=tenant_id,
            )


class TestCommandLifecycle:
    """Test command state transitions."""

    @pytest.mark.asyncio
    async def test_send_command(self, command_service, mock_session, mock_registry):
        command_id = uuid4()
        tenant_id = uuid4()

        command = TwinCommand(
            tenant_id=tenant_id,
            twin_binding_id=uuid4(),
            target_device_id=uuid4(),
            command_type="write",
            payload={},
            status="created",
        )
        command.id = command_id
        command_service._command_repo.get_by_id_for_tenant = AsyncMock(return_value=command)

        result = await command_service.send_command(command_id, tenant_id)
        assert result.status == "sent"

    @pytest.mark.asyncio
    async def test_acknowledge_command(self, command_service, mock_session, mock_registry):
        command_id = uuid4()
        tenant_id = uuid4()

        command = TwinCommand(
            tenant_id=tenant_id,
            twin_binding_id=uuid4(),
            target_device_id=uuid4(),
            command_type="write",
            payload={},
            status="sent",
        )
        command.id = command_id
        command_service._command_repo.get_by_id_for_tenant = AsyncMock(return_value=command)

        result = await command_service.acknowledge_command(command_id, tenant_id)
        assert result.status == "acknowledged"

    @pytest.mark.asyncio
    async def test_fail_command(self, command_service, mock_session, mock_registry):
        command_id = uuid4()
        tenant_id = uuid4()

        command = TwinCommand(
            tenant_id=tenant_id,
            twin_binding_id=uuid4(),
            target_device_id=uuid4(),
            command_type="write",
            payload={},
            status="sent",
        )
        command.id = command_id
        command_service._command_repo.get_by_id_for_tenant = AsyncMock(return_value=command)

        result = await command_service.fail_command(command_id, tenant_id, "Device unreachable")
        assert result.status == "failed"
        assert result.error_message == "Device unreachable"

    @pytest.mark.asyncio
    async def test_command_not_found(self, command_service, mock_session, mock_registry):
        command_id = uuid4()
        tenant_id = uuid4()

        command_service._command_repo.get_by_id_for_tenant = AsyncMock(return_value=None)

        from services.activation.exceptions import CommandNotFoundError
        with pytest.raises(CommandNotFoundError):
            await command_service.get_command(command_id, tenant_id)
