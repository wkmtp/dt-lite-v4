"""TwinCommandService — Command lifecycle management."""
import logging
from datetime import datetime, timezone
from uuid import UUID

from services.activation.exceptions import (
    CommandNotFoundError,
    ActivationNotFoundError,
    BindingNotActiveError,
)
from services.activation.models import TwinCommand
from services.activation.repository import TwinCommandRepository
from services.activation.services import TwinActivationService
from services.twin.repositories.binding_repository import BindingRepository

logger = logging.getLogger(__name__)

# Command lifecycle states
VALID_COMMAND_TRANSITIONS = {
    "created": {"sent", "failed"},
    "sent": {"acknowledged", "failed"},
    "acknowledged": set(),
    "failed": set(),
}


def validate_command_transition(current_state: str, target_state: str) -> bool:
    """Validate if a command state transition is allowed."""
    allowed = VALID_COMMAND_TRANSITIONS.get(current_state, set())
    return target_state in allowed


class TwinCommandService:
    """Manages the command lifecycle from creation to execution tracking.

    Command flow:
      1. Client creates TwinCommand (status=CREATED)
      2. Service validates binding is active
      3. Service attempts to send via adapter contract (stub in Task 14)
      4. Service updates status to SENT/FAILED

    NOTE: Actual adapter communication (ProtocolAdapter.write) is delegated
    to the Adapter layer (Task 15+). Task 14 only creates command intent.
    """

    def __init__(self, session, registry):
        self._session = session
        self._command_repo = TwinCommandRepository(session)
        self._binding_repo = BindingRepository(session)
        self._activation_service = TwinActivationService(session, registry)

    async def create_command(
        self,
        binding_id: UUID,
        target_device_id: UUID,
        command_type: str,
        payload: dict,
        tenant_id: UUID,
    ) -> TwinCommand:
        """Create a new TwinCommand intent.

        Validates:
          - Binding exists and belongs to tenant
          - Binding is active (entity is in runtime registry)
          - Device belongs to tenant
        """
        # Validate binding
        binding = await self._binding_repo.get_by_id_for_tenant(binding_id, tenant_id)
        if binding is None:
            raise ActivationNotFoundError(binding_id)

        # Validate binding's entity is active
        activation_log = await self._activation_service.get_status(
            binding.twin_entity_id, tenant_id,
        )
        if activation_log.state != "active":
            raise BindingNotActiveError(binding_id)

        # Create command
        command = TwinCommand(
            tenant_id=tenant_id,
            twin_binding_id=binding_id,
            target_device_id=target_device_id,
            command_type=command_type,
            payload=payload,
            status="created",
        )
        command = await self._command_repo.create(command)
        logger.info("Created command %s for binding %s", command.id, binding_id)
        return command

    async def send_command(
        self, command_id: UUID, tenant_id: UUID,
    ) -> TwinCommand:
        """Transition command from CREATED to SENT.

        In Task 14, this is a stub — actual adapter communication
        is delegated to the Adapter layer (Task 15+).
        """
        command = await self._command_repo.get_by_id_for_tenant(command_id, tenant_id)
        if command is None:
            raise CommandNotFoundError(command_id)

        if command.status != "created":
            raise RuntimeError(f"Cannot send command in status '{command.status}'")

        command.status = "sent"
        command.updated_at = datetime.now(timezone.utc)
        await self._command_repo.session.flush()

        logger.info("Sent command %s for binding %s", command_id, command.twin_binding_id)
        return command

    async def acknowledge_command(
        self, command_id: UUID, tenant_id: UUID,
    ) -> TwinCommand:
        """Transition command from SENT to ACKNOWLEDGED."""
        command = await self._command_repo.get_by_id_for_tenant(command_id, tenant_id)
        if command is None:
            raise CommandNotFoundError(command_id)

        if command.status != "sent":
            raise RuntimeError(f"Cannot acknowledge command in status '{command.status}'")

        command.status = "acknowledged"
        command.executed_at = datetime.now(timezone.utc)
        command.updated_at = datetime.now(timezone.utc)
        await self._command_repo.session.flush()

        logger.info("Acknowledged command %s", command_id)
        return command

    async def fail_command(
        self, command_id: UUID, tenant_id: UUID, error_message: str,
    ) -> TwinCommand:
        """Transition command to FAILED with error message."""
        command = await self._command_repo.get_by_id_for_tenant(command_id, tenant_id)
        if command is None:
            raise CommandNotFoundError(command_id)

        if command.status not in ("created", "sent"):
            raise RuntimeError(f"Cannot fail command in status '{command.status}'")

        command.status = "failed"
        command.error_message = error_message
        command.executed_at = datetime.now(timezone.utc)
        command.updated_at = datetime.now(timezone.utc)
        await self._command_repo.session.flush()

        logger.warning("Command %s failed: %s", command_id, error_message)
        return command

    async def get_command(
        self, command_id: UUID, tenant_id: UUID,
    ) -> TwinCommand:
        """Get a command by ID."""
        command = await self._command_repo.get_by_id_for_tenant(command_id, tenant_id)
        if command is None:
            raise CommandNotFoundError(command_id)
        return command
