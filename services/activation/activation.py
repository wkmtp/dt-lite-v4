"""TwinActivation — Activation helpers and state validation."""


# Activation state machine definition
VALID_TRANSITIONS = {
    "created": {"bound", "active", "error"},
    "bound": {"active", "error"},
    "active": {"inactive", "error"},
    "inactive": {"active"},
    "error": {"created", "bound"},
}


def validate_transition(current_state: str, target_state: str) -> bool:
    """Validate if a state transition is allowed."""
    allowed = VALID_TRANSITIONS.get(current_state, set())
    return target_state in allowed


def get_activation_states() -> list[str]:
    """Return all valid activation states."""
    return list(VALID_TRANSITIONS.keys())


def is_terminal_state(state: str) -> bool:
    """Check if a state is terminal (no further transitions except error recovery)."""
    return state in ("inactive",)
