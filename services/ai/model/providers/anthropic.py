"""Anthropic Claude provider adapter."""

from __future__ import annotations

import logging
from typing import Any, AsyncIterator, Optional

import httpx

logger = logging.getLogger(__name__)


class AnthropicProvider:
    """Adapter for Anthropic Messages API."""

    def __init__(self, *, api_key: Optional[str] = None, base_url: Optional[str] = None) -> None:
        self._api_key = api_key or ""
        self._base_url = (base_url or "https://api.anthropic.com").rstrip("/")

    async def chat(self, *, model: str, messages: list[dict[str, Any]], temperature: float, max_tokens: int) -> dict[str, Any]:
        # Anthropic uses system + messages format
        system_msg = next((m for m in messages if m.get("role") == "system"), None)
        conversation = [m for m in messages if m.get("role") != "system"]
        payload: dict[str, Any] = {
            "model": model,
            "messages": conversation,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        if system_msg:
            payload["system"] = system_msg["content"]

        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                f"{self._base_url}/v1/messages",
                headers=self._headers(),
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()
            text = _extract_text(data)
            return {
                "provider": "anthropic",
                "model": model,
                "message": {"role": "assistant", "content": text},
                "usage": data.get("usage", {}),
            }

    async def chat_stream(
        self,
        *,
        model: str,
        messages: list[dict[str, Any]],
        temperature: float,
        max_tokens: int,
    ) -> AsyncIterator[dict[str, Any]]:
        system_msg = next((m for m in messages if m.get("role") == "system"), None)
        conversation = [m for m in messages if m.get("role") != "system"]
        payload: dict[str, Any] = {
            "model": model,
            "messages": conversation,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": True,
        }
        if system_msg:
            payload["system"] = system_msg["content"]

        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream(
                "POST",
                f"{self._base_url}/v1/messages",
                headers=self._headers(),
                json=payload,
            ) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    import json
                    try:
                        event = json.loads(line[len("data: "):])
                        yield _normalize_event(event)
                    except Exception:
                        continue

    def _headers(self) -> dict[str, str]:
        return {
            "x-api-key": self._api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        }


def _extract_text(data: dict[str, Any]) -> str:
    for block in data.get("content", []):
        if block.get("type") == "text":
            return block.get("text", "")
    return ""


def _normalize_event(event: dict[str, Any]) -> dict[str, Any]:
    """Normalize Anthropic SSE events to a common chunk shape."""
    etype = event.get("type")
    if etype == "content_block_delta":
        return {
            "provider": "anthropic",
            "model": event.get("model"),
            "delta": {"content": event.get("delta", {}).get("text", "")},
            "finish_reason": None,
        }
    if etype == "message_stop":
        return {
            "provider": "anthropic",
            "model": event.get("model"),
            "delta": {},
            "finish_reason": "stop",
            "usage": event.get("message", {}).get("usage"),
        }
    if etype == "message_start":
        return {
            "provider": "anthropic",
            "model": event.get("model"),
            "delta": {},
            "usage": event.get("message", {}).get("usage"),
        }
    return {}
