"""Adapter Lifecycle State Machine.

Valid transitions:
  CREATED ──connect──► CONNECTED ──start──► RUNNING
                                                │
                                                ▼
  STOPPED ◄──stop── RUNNING ◄──disconnect── FAILED
       │                              │
       └───────reset──────────────────┘

Transitions that are NOT allowed will raise AdapterLifecycleError.
"""
from enum import Enum
from typing import Any, Callable


class LifecycleState(str, Enum):
    """Adapter lifecycle states."""
    CREATED = "CREATED"
    CONNECTED = "CONNECTED"
    RUNNING = "RUNNING"
    STOPPED = "STOPPED"
    FAILED = "FAILED"


class AdapterLifecycle:
    """State machine managing adapter lifecycle transitions.

    This class enforces valid state transitions and coordinates
    with the adapter's connect/disconnect/start/stop methods.
    """

    # Valid transition map: current_state -> set of allowed next states
    VALID_TRANSITIONS = {
        LifecycleState.CREATED: {LifecycleState.CONNECTED},
        LifecycleState.CONNECTED: {LifecycleState.RUNNING},
        LifecycleState.RUNNING: {LifecycleState.STOPPED, LifecycleState.FAILED},
        LifecycleState.STOPPED: {LifecycleState.CREATED},
        LifecycleState.FAILED: {LifecycleState.CREATED},
    }

    def __init__(self, name: str):
        self._name = name
        self._state = LifecycleState.CREATED
        self._handlers: dict[str, Callable] = {}

    @property
    def name(self) -> str:
        return self._name

    @property
    def state(self) -> LifecycleState:
        return self._state

    def can_transition(self, target: LifecycleState) -> bool:
        """Check if transition to target state is valid."""
        allowed = self.VALID_TRANSITIONS.get(self._state, set())
        return target in allowed

    async def connect(self, adapter: Any, endpoint: str, credentials_ref: str, config: dict) -> None:
        """Transition from CREATED to CONNECTED."""
        if not self.can_transition(LifecycleState.CONNECTED):
            from services.adapter.exceptions import AdapterLifecycleError
            raise AdapterLifecycleError(
                self._name, self._state.value, LifecycleState.CONNECTED.value
            )

        try:
            await adapter.connect(endpoint, credentials_ref, config)
            self._state = LifecycleState.CONNECTED
        except Exception as e:
            from services.adapter.exceptions import AdapterConnectionError
            raise AdapterConnectionError(self._name, cause=e) from e

    async def start(self, adapter: Any) -> None:
        """Transition from CONNECTED to RUNNING.

        Note: For sync adapters, 'start' is a no-op after connect.
        For future async adapters, this could trigger background tasks.
        """
        if not self.can_transition(LifecycleState.RUNNING):
            from services.adapter.exceptions import AdapterLifecycleError
            raise AdapterLifecycleError(
                self._name, self._state.value, LifecycleState.RUNNING.value
            )
        self._state = LifecycleState.RUNNING

    async def stop(self, adapter: Any) -> None:
        """Transition from RUNNING to STOPPED."""
        if not self.can_transition(LifecycleState.STOPPED):
            from services.adapter.exceptions import AdapterLifecycleError
            raise AdapterLifecycleError(
                self._name, self._state.value, LifecycleState.STOPPED.value
            )
        await adapter.disconnect()
        self._state = LifecycleState.STOPPED

    async def reset(self, adapter: Any) -> None:
        """Transition from FAILED/STOPPED back to CREATED."""
        if self._state not in (LifecycleState.FAILED, LifecycleState.STOPPED):
            # Already at CREATED, just reset
            if self._state == LifecycleState.CREATED:
                return
            from services.adapter.exceptions import AdapterLifecycleError
            raise AdapterLifecycleError(
                self._name, self._state.value, LifecycleState.CREATED.value
            )

        # Try to disconnect if still connected
        if self._state == LifecycleState.FAILED:
            try:
                await adapter.disconnect()
            except Exception:
                pass  # Best effort cleanup

        self._state = LifecycleState.CREATED

    def mark_failed(self, error_msg: str) -> None:
        """Mark adapter as FAILED (for use when async errors occur)."""
        if self._state != LifecycleState.RUNNING:
            return  # Only running adapters can fail
        self._state = LifecycleState.FAILED
