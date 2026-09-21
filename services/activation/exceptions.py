"""Activation layer custom exceptions."""
from uuid import UUID


class ActivationError(Exception):
    """Base exception for activation layer errors."""

    def __init__(self, message: str, code: str = "ACTIVATION_ERROR"):
        self.code = code
        self.message = message
        super().__init__(self.message)


class ActivationNotFoundError(ActivationError):
    """Activation log not found."""

    def __init__(self, entity_id: UUID):
        super().__init__(
            f"Activation log for entity {entity_id} not found",
            code="ACTIVATION_NOT_FOUND",
        )


class ActivationStateError(ActivationError):
    """Invalid state transition for activation."""

    def __init__(self, entity_id: UUID, current_state: str, expected_state: str):
        super().__init__(
            f"Entity {entity_id} is in state '{current_state}', "
            f"expected '{expected_state}'",
            code="ACTIVATION_STATE_ERROR",
        )


class ActivationAlreadyActiveError(ActivationError):
    """Entity is already active."""

    def __init__(self, entity_id: UUID):
        super().__init__(
            f"Entity {entity_id} is already active",
            code="ACTIVATION_ALREADY_ACTIVE",
        )


class ActivationAlreadyInactiveError(ActivationError):
    """Entity is already inactive."""

    def __init__(self, entity_id: UUID):
        super().__init__(
            f"Entity {entity_id} is already inactive",
            code="ACTIVATION_ALREADY_INACTIVE",
        )


class CommandNotFoundError(ActivationError):
    """Command not found."""

    def __init__(self, command_id: UUID):
        super().__init__(
            f"Command {command_id} not found",
            code="COMMAND_NOT_FOUND",
        )


class CommandSendError(ActivationError):
    """Command send failed."""

    def __init__(self, command_id: UUID, reason: str):
        super().__init__(
            f"Command {command_id} send failed: {reason}",
            code="COMMAND_SEND_ERROR",
        )


class BindingNotActiveError(ActivationError):
    """Binding is not active, cannot send command."""

    def __init__(self, binding_id: UUID):
        super().__init__(
            f"Binding {binding_id} is not active",
            code="BINDING_NOT_ACTIVE",
        )
