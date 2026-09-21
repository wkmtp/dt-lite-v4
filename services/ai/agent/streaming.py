"""SSE (Server-Sent Events) streaming response generator.

Wraps async generators into the SSE wire format so that clients
receive incremental updates as the agent produces tokens.
"""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, AsyncIterator, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# SSE helpers
# ---------------------------------------------------------------------------

def _sse_event(
    event: str,
    data: Any,
    event_id: Optional[str] = None,
    retry: Optional[int] = None,
) -> str:
    """Format a single SSE event as a string."""
    lines: list[str] = []
    if event_id:
        lines.append(f"id: {event_id}")
    if retry is not None:
        lines.append(f"retry: {retry}")
    lines.append(f"event: {event}")
    if isinstance(data, (dict, list)):
        data = json.dumps(data)
    for line in str(data).splitlines():
        lines.append(f"data: {line}")
    lines.append("")  # trailing blank line terminates the event
    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# SSEStreamGenerator
# ---------------------------------------------------------------------------

class SSEStreamGenerator:
    """Generates SSE-formatted streams from async iterables.

    Produces the following event types:
      - ``token``       : individual text chunks
      - ``tool_call``   : tool invocation details
      - ``tool_result`` : tool execution output
      - ``step``        : ReAct step boundaries
      - ``done``        : stream finalisation
      - ``error``       : error information
    """

    def __init__(
        self,
        stream_id: str,
        retry_ms: int = 3000,
    ) -> None:
        self._stream_id = stream_id
        self._retry_ms = retry_ms
        self._event_counter = 0

    def _next_id(self) -> str:
        self._event_counter += 1
        return f"{self._stream_id}-{self._event_counter}"

    async def generate(
        self,
        agent_async_iterator: AsyncIterator[str],
    ) -> AsyncIterator[str]:
        """Wrap an async text iterator in SSE events.

        Args:
            agent_async_iterator: An async generator yielding text chunks.

        Yields:
            SSE-formatted event strings.
        """
        try:
            async for chunk in agent_async_iterator:
                yield _sse_event(
                    event="token",
                    data=chunk,
                    event_id=self._next_id(),
                    retry=self._retry_ms,
                )
        except Exception as exc:
            logger.error("SSE stream error for %s: %s", self._stream_id, exc, exc_info=True)
            yield _sse_event(
                event="error",
                data={"message": str(exc), "stream_id": self._stream_id},
                event_id=self._next_id(),
            )
        finally:
            yield _sse_event(
                event="done",
                data={"stream_id": self._stream_id, "status": "complete"},
                event_id=self._next_id(),
            )

    async def generate_with_metadata(
        self,
        agent_async_iterator: AsyncIterator[str],
        metadata: Optional[dict[str, Any]] = None,
    ) -> AsyncIterator[str]:
        """Generate SSE stream including initial metadata event."""
        if metadata:
            yield _sse_event(
                event="metadata",
                data=metadata,
                event_id=self._next_id(),
            )
        async for event in self.generate(agent_async_iterator):
            yield event
