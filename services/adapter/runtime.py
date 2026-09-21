"""Adapter Runtime — Connection pooling, retry, circuit breaker."""
import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional

from services.iota.contracts import ProtocolAdapter
from services.adapter.exceptions import AdapterConnectionError

logger = logging.getLogger(__name__)

# Circuit breaker states
STATE_CLOSED = "closed"
STATE_OPEN = "open"
STATE_HALF_OPEN = "half_open"


class CircuitBreaker:
    """Simple circuit breaker for adapter connections."""

    def __init__(self, max_failures: int = 5, reset_timeout: float = 30.0):
        self._max_failures = max_failures
        self._reset_timeout = reset_timeout
        self._state = STATE_CLOSED
        self._failure_count = 0
        self._last_failure_time: Optional[datetime] = None
        self._lock = asyncio.Lock()

    @property
    def state(self) -> str:
        if self._state == STATE_OPEN and self._last_failure_time:
            elapsed = (datetime.now(timezone.utc) - self._last_failure_time).total_seconds()
            if elapsed >= self._reset_timeout:
                return STATE_HALF_OPEN
        return self._state

    async def record_success(self) -> None:
        async with self._lock:
            self._failure_count = 0
            if self._state in (STATE_HALF_OPEN, STATE_OPEN):
                self._state = STATE_CLOSED
                logger.info("Circuit breaker CLOSED")

    async def record_failure(self) -> None:
        async with self._lock:
            self._failure_count += 1
            self._last_failure_time = datetime.now(timezone.utc)
            if self._failure_count >= self._max_failures:
                self._state = STATE_OPEN
                logger.warning("Circuit breaker OPEN after %d failures", self._failure_count)

    async def allow_request(self) -> bool:
        current_state = self.state
        if current_state == STATE_CLOSED:
            return True
        if current_state == STATE_HALF_OPEN:
            return True
        return False


class AdapterRuntime:
    """Manages adapter connection lifecycle with retry and circuit breaking."""

    def __init__(
        self,
        max_retries: int = 3,
        base_retry_delay: float = 1.0,
        circuit_breaker_max_failures: int = 5,
        circuit_breaker_reset_timeout: float = 30.0,
    ):
        self._max_retries = max_retries
        self._base_retry_delay = base_retry_delay
        self._circuit_breaker = CircuitBreaker(
            max_failures=circuit_breaker_max_failures,
            reset_timeout=circuit_breaker_reset_timeout,
        )

    async def connect_with_retry(
        self,
        adapter: ProtocolAdapter,
        endpoint: str,
        credentials_ref: str,
        config: dict,
    ) -> None:
        last_error = None
        for attempt in range(self._max_retries):
            try:
                await adapter.connect(endpoint, credentials_ref, config)
                await self._circuit_breaker.record_success()
                logger.info("Adapter connected to %s (attempt %d/%d)", endpoint, attempt + 1, self._max_retries)
                return
            except Exception as e:
                last_error = e
                await self._circuit_breaker.record_failure()
                if attempt < self._max_retries - 1:
                    delay = self._base_retry_delay * (2 ** attempt)
                    logger.warning("Adapter connection attempt %d/%d failed for %s: %s. Retrying in %.1fs...",
                                   attempt + 1, self._max_retries, endpoint, e, delay)
                    await asyncio.sleep(delay)

        raise AdapterConnectionError(endpoint, str(last_error))

    async def disconnect_with_cleanup(self, adapter: ProtocolAdapter) -> None:
        try:
            await adapter.disconnect()
            logger.info("Adapter disconnected successfully")
        except Exception as e:
            logger.warning("Error during adapter disconnect: %s", e)

    async def check_health(self, adapter: ProtocolAdapter) -> bool:
        if not await self._circuit_breaker.allow_request():
            logger.warning("Circuit breaker OPEN — health check skipped")
            return False
        try:
            healthy = await adapter.health()
            if healthy:
                await self._circuit_breaker.record_success()
            else:
                await self._circuit_breaker.record_failure()
            return healthy
        except Exception as e:
            await self._circuit_breaker.record_failure()
            logger.warning("Health check failed: %s", e)
            return False

    @property
    def circuit_state(self) -> str:
        return self._circuit_breaker.state
