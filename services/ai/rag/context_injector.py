"""ContextInjector: dynamic context window management for LLM prompts."""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional, Sequence

from pydantic import BaseModel, Field


SYSTEM_PROMPT_TAKE = 4096  # reserve 4k tokens for system prompt + user input + tool responses
DEFAULT_CONTEXT_WINDOW = 32768


@dataclass
class ContextItem:
    """A single item in the injected context."""
    text: str
    score: float
    metadata: dict = field(default_factory=dict)


class ContextConfig(BaseModel):
    """Configuration for context injection."""
    context_window: int = Field(default=DEFAULT_CONTEXT_WINDOW, ge=1024)
    system_prompt_take: int = Field(default=SYSTEM_PROMPT_TAKE, ge=0)
    max_context_tokens: int = Field(default=16384, ge=0)
    min_chunk_token_size: int = Field(default=50, ge=1)


class ContextInjector:
    """
    Manages a dynamic context window, reserving tokens for system prompt,
    user input, and tool responses. Provides token estimation and context
    selection from retrieved documents.
    """

    def __init__(self, config: Optional[ContextConfig] = None) -> None:
        self._config = config or ContextConfig()

    def estimate_tokens(self, text: str) -> int:
        """Rough token count: 1 token ≈ 4 characters for English, ~2 for CJK."""
        cjk_chars = sum(1 for ch in text if '\u4e00' <= ch <= '\u9fff' or '\u3000' <= ch <= '\u303f' or '\uff00' <= ch <= '\uffef')
        non_cjk = len(text) - cjk_chars
        return max(1, (cjk_chars // 2) + (non_cjk // 4))

    def build_context(
        self,
        documents: Sequence[ContextItem],
        *,
        query: str,
        system_prompt: str = "",
        available_tokens: Optional[int] = None,
    ) -> str:
        """
        Build the final context string, respecting the configurable context window.
        Returns the concatenated context; caller is responsible for ensuring the
        total prompt (system + query + context + tool response budget) fits.
        """
        budget = available_tokens or self._config.max_context_tokens
        remaining = budget
        parts: list[str] = []
        for item in sorted(documents, key=lambda x: x.score, reverse=True):
            tok = self.estimate_tokens(item.text)
            if tok > remaining:
                continue
            parts.append(item.text)
            remaining -= tok
        context = "\n\n---\n\n".join(parts)
        return context

    def check_fit(
        self,
        system_prompt: str,
        query: str,
        context: str,
        estimated_tool_response_tokens: int = 1024,
    ) -> bool:
        """Return True if the total prompt fits within the context window."""
        total = (
            self.estimate_tokens(system_prompt)
            + self.estimate_tokens(query)
            + self.estimate_tokens(context)
            + estimated_tool_response_tokens
        )
        return total <= self._config.context_window

    def reserve_budget(
        self,
        system_prompt: str,
        query: str,
    ) -> int:
        """Return the number of tokens reserved for context after accounting for system + query."""
        used = (
            self.estimate_tokens(system_prompt)
            + self.estimate_tokens(query)
            + SYSTEM_PROMPT_TAKE  # tool response budget
        )
        return max(0, self._config.context_window - used)
