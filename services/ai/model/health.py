"""HealthChecker and circuit breaker for model providers.

Implements R6: all LLM calls async with timeout + circuit breaker.
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger(__name__)


class CircuitState(str, Enum):
    CLOSED = "closed"      # normal
    OPEN = "open"          # failing, reject requests
    HALF_OPEN = "half_open"  # testing recovery


@dataclass
class ProviderHealth:
    state: CircuitState = CircuitState.CLOSED
    failure_count: int = 0
    last_failure_time: float = 0.0
    success_count: int = 0
    last_success_time: float = 0.0
    error_threshold: int = 5
    timeout_s: float = 30.0
    recovery_timeout_s: float = 60.0


class HealthChecker:
    """Per-provider circuit breaker with half-open recovery testing."""

    def __init__(self, error_threshold: int = 5, recovery_timeout_s: float = 60.0) -> None:
        self._error_threshold = error_threshold
        self._recovery_timeout_s = recovery_timeout_s
        self._circuits: dict[str, ProviderHealth] = {}
        self._lock = asyncio.Lock()

    async def register_provider(self, provider: str, _adapter: Any) -> None:
        async with self._lock:
            if provider not in self._circuits:
                self._circuits[provider] = ProviderHealth()

    def get_circuit(self, provider: str) -> CircuitState:
        circuit = self._circuits.get(provider)
        if circuit is None:
            return CircuitState.CLOSED
        # Auto-transition OPEN -> HALF_OPEN after recovery timeout
        if circuit.state == CircuitState.OPEN:
            if time.monotonic() - circuit.last_failure_time >= self._recovery_timeout_s:
                circuit.state = CircuitState.HALF_OPEN
                logger.info("circuit %s transitioned to HALF_OPEN", provider)
        return circuit.state

    def record_success(self, provider: str) -> None:
        circuit = self._circuits.get(provider)
        if circuit is None:
            return
        circuit.failure_count = 0
        circuit.success_count += 1
        circuit.last_success_time = time.monotonic()
        if circuit.state == CircuitState.HALF_OPEN:
            circuit.state = CircuitState.CLOSED
            logger.info("circuit %s closed after recovery", provider)

    def record_failure(self, provider: str) -> None:
        circuit = self._circuits.get(provider)
        if circuit is None:
            return
        circuit.failure_count += 1
        circuit.last_failure_time = time.monotonic()
        if circuit.state != CircuitState.OPEN and circuit.failure_count >= self._error_threshold:
            circuit.state = CircuitState.OPEN
            logger.warning("circuit %s opened after %d failures", provider, circuit.failure_count)

    def trip_circuit(self, provider: str) -> None:
        """Force-open circuit (e.g. quota exceeded)."""
        circuit = self._circuits.get(provider)
        if circuit is None:
            return
        circuit.state = CircuitState.OPEN
        circuit.last_failure_time = time.monotonic()
        logger.warning("circuit %s tripped manually", provider)

    def close_circuit(self, provider: str) -> None:
        circuit = self._circuits.get(provider)
        if circuit is None:
            return
        circuit.state = CircuitState.CLOSED
        circuit.failure_count = 0

    async def health_check(self, provider: str) -> dict[str, Any]:
        circuit = self._circuits.get(provider)
        if circuit is None:
            return {"provider": provider, "available": False, "state": "unknown"}
        return {
            "provider": provider,
            "available": circuit.state != CircuitState.OPEN,
            "state": circuit.state.value,
            "failure_count": circuit.failure_count,
            "success_count": circuit.success_count,
        }

    @property
    def _circuits(self) -> dict[str, ProviderHealth]:
        return self._circuits  # type: ignore[return-value]
