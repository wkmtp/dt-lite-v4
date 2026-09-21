"""vLLM / TGI provider adapter.

vLLM serves an OpenAI-compatible API; TGI uses a different endpoint.
This adapter targets vLLM's OpenAI-compatible endpoint by default.
"""

from __future__ import annotations

import logging
from typing import Any, AsyncIterator, Optional

import httpx

logger = logging.getLogger(__name__)


class VLLMProvider:
    """Adapter for vLLM/OpenAI-compatible serving endpoints (vLLM, TGI via compat layer)."""

    def __init__(self, *, base_url: Optional[str] = None) -> None:
        self._base_url = (base_url or "http://localhost:8000/v1").rstrip("/")

    async def chat(self, *, model: str, messages: list[dict[str, Any]], temperature: float, max_tokens: int) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                f"{self._base_url}/chat/completions",
                headers={"Content-Type": "application/json"},
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
                "provider": "vllm",
                "model": model,
                "choices": data.get("choices", []),
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
        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream(
                "POST",
                f"{self._base_url}/chat/completions",
                headers={"Content-Type": "application/json"},
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
                    import json
                    try:
                        chunk = json.loads(payload)
                        choice = (chunk.get("choices") or [{}])[0]
                        yield {
                            "provider": "vllm",
                            "model": chunk.get("model"),
                            "delta": choice.get("delta", {}),
                            "finish_reason": choice.get("finish_reason"),
                            "usage": chunk.get("usage"),
                        }
                    except Exception:
                        continue
