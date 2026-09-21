"""OpenAI-compatible provider adapter.

Supports OpenAI native API and any OpenAI-compatible endpoint (vLLM, Ollama, Azure OpenAI).
"""

from __future__ import annotations

import logging
from typing import Any, AsyncIterator, Optional

import httpx

logger = logging.getLogger(__name__)


class OpenAIProvider:
    """Adapter for OpenAI Chat Completions API (also works with compatible endpoints)."""

    def __init__(self, *, api_key: Optional[str] = None, base_url: Optional[str] = None) -> None:
        self._api_key = api_key or ""
        self._base_url = (base_url or "https://api.openai.com/v1").rstrip("/")

    async def chat(self, *, model: str, messages: list[dict[str, Any]], temperature: float, max_tokens: int) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                f"{self._base_url}/chat/completions",
                headers=self._headers(),
                json={
                    "model": model,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                    "stream": False,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            return {
                "provider": "openai",
                "model": model,
                "choices": data.get("choices", []),
                "usage": data.get("usage", {}),
                "finish_reason": data.get("choices", [{}])[0].get("finish_reason") if data.get("choices") else None,
            }

    async def chat_stream(
        self,
        *,
        model: str,
        messages: list[dict[str, Any]],
        temperature: float,
        max_tokens: int,
    ) -> AsyncIterator[dict[str, Any]]:
        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream(
                "POST",
                f"{self._base_url}/chat/completions",
                headers=self._headers(),
                json={
                    "model": model,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                    "stream": True,
                },
            ) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line or not line.startswith("data: "):
                        continue
                    payload = line[len("data: "):]
                    if payload.strip() == "[DONE]":
                        break
                    try:
                        chunk = json_loads(payload)
                        yield _normalize_chunk(chunk)
                    except Exception:
                        continue

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }


def json_loads(s: str) -> Any:
    import json
    return json.loads(s)


def _normalize_chunk(chunk: dict[str, Any]) -> dict[str, Any]:
    """Normalize to SSE event dict consumable by the gateway."""
    choice = (chunk.get("choices") or [{}])[0]
    return {
        "provider": "openai",
        "model": chunk.get("model"),
        "delta": choice.get("delta", {}),
        "finish_reason": choice.get("finish_reason"),
        "usage": chunk.get("usage"),
    }
