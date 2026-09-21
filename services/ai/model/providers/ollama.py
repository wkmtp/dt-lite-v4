"""Ollama provider adapter.

Ollama exposes an OpenAI-compatible /api/chat endpoint and a native /api/generate endpoint.
We target the native endpoint for simplicity and broad compatibility.
"""

from __future__ import annotations

import logging
from typing import Any, AsyncIterator, Optional

import httpx

logger = logging.getLogger(__name__)


class OllamaProvider:
    """Adapter for Ollama local inference server."""

    def __init__(self, *, base_url: Optional[str] = None) -> None:
        self._base_url = (base_url or "http://localhost:11434").rstrip("/")

    async def chat(self, *, model: str, messages: list[dict[str, Any]], temperature: float, max_tokens: int) -> dict[str, Any]:
        ollama_msgs = [_to_ollama_msg(m) for m in messages]
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                f"{self._base_url}/api/chat",
                json={
                    "model": model,
                    "messages": ollama_msgs,
                    "options": {
                        "temperature": temperature,
                        "num_predict": max_tokens,
                    },
                    "stream": False,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            return {
                "provider": "ollama",
                "model": model,
                "message": {"role": "assistant", "content": data.get("message", {}).get("content", "")},
                "usage": {
                    "prompt_tokens": data.get("prompt_eval_count", 0),
                    "completion_tokens": data.get("eval_count", 0),
                    "total_tokens": (data.get("prompt_eval_count") or 0) + (data.get("eval_count") or 0),
                },
            }

    async def chat_stream(
        self,
        *,
        model: str,
        messages: list[dict[str, Any]],
        temperature: float,
        max_tokens: int,
    ) -> AsyncIterator[dict[str, Any]]:
        ollama_msgs = [_to_ollama_msg(m) for m in messages]
        async with httpx.AsyncClient(timeout=180.0) as client:
            async with client.stream(
                "POST",
                f"{self._base_url}/api/chat",
                json={
                    "model": model,
                    "messages": ollama_msgs,
                    "options": {
                        "temperature": temperature,
                        "num_predict": max_tokens,
                    },
                    "stream": True,
                },
            ) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line:
                        continue
                    import json
                    try:
                        chunk = json.loads(line)
                        yield {
                            "provider": "ollama",
                            "model": model,
                            "delta": {"content": chunk.get("message", {}).get("content", "")},
                            "finish_reason": None if not chunk.get("done") else "stop",
                            "usage": {
                                "prompt_tokens": chunk.get("prompt_eval_count", 0),
                                "completion_tokens": chunk.get("eval_count", 0),
                                "total_tokens": (chunk.get("prompt_eval_count") or 0) + (chunk.get("eval_count") or 0),
                            } if chunk.get("done") else None,
                        }
                    except Exception:
                        continue


def _to_ollama_msg(msg: dict[str, Any]) -> dict[str, Any]:
    """Map generic message to Ollama message format."""
    role = msg.get("role", "user")
    content = msg.get("content", "")
    return {"role": role, "content": content}
