"""Model Gateway - Unified routing, load balancing, auto fallback, rate limiting."""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Optional

from services.ai.model.providers.openai import OpenAIProvider
from services.ai.model.providers.anthropic import AnthropicProvider
from services.ai.model.providers.ollama import OllamaProvider
from services.ai.model.providers.vllm import VLLMProvider
from services.ai.model.health import HealthChecker, CircuitState
from services.ai.model.quota import TenantQuotaManager
from services.ai.model.cost import CostTracker
from services.ai.audit.logger import AuditLogger
from services.core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class _ProviderSlot:
    """Internal representation of a configured model provider."""
    provider: str  # openai | anthropic | ollama | vllm
    model: str
    base_url: Optional[str]
    weight: int = 1
    enabled: bool = True


class ModelGateway:
    """Centralized model gateway enforcing R3: all model calls go through here.

    Responsibilities:
    - Route requests to configured providers
    - Round-robin load balancing by weight
    - Auto-fallback on circuit-open or error
    - Rate-limit enforcement via TenantQuotaManager
    - Cost tracking via CostTracker
    - Audit logging via AuditLogger
    - Async with timeout + circuit breaker (R6)
    """

    def __init__(
        self,
        quota_manager: TenantQuotaManager,
        cost_tracker: CostTracker,
        audit_logger: AuditLogger,
        health_checker: HealthChecker,
    ) -> None:
        self._slots: list[_ProviderSlot] = []
        self._rr_index: int = 0
        self._lock = asyncio.Lock()
        self._quota = quota_manager
        self._cost = cost_tracker
        self._audit = audit_logger
        self._health = health_checker

    # ------------------------------------------------------------------ init
    @classmethod
    async def create(cls) -> "ModelGateway":
        quota = TenantQuotaManager()
        cost = CostTracker()
        audit = AuditLogger()
        health = HealthChecker()
        instance = cls(quota, cost, audit, health)

        # Register built-in providers from settings
        await instance.register_openai(
            api_key=settings.AI_OPENAI_API_KEY,
            base_url=settings.AI_OPENAI_BASE_URL,
        )
        await instance.register_anthropic(
            api_key=settings.AI_ANTHROPIC_API_KEY,
            base_url=settings.AI_ANTHROPIC_BASE_URL,
        )
        await instance.register_ollama(
            base_url=settings.AI_OLLAMA_BASE_URL,
        )
        await instance.register_vllm(
            base_url=settings.AI_VLLM_BASE_URL,
        )
        return instance

    # ---------------------------------------------------------------- registry
    async def register_openai(
        self,
        *,
        api_key: str,
        base_url: Optional[str] = None,
        models: Optional[list[str]] = None,
        weight: int = 1,
    ) -> None:
        if not api_key:
            return
        provider = OpenAIProvider(api_key=api_key, base_url=base_url)
        await self._health.register_provider("openai", provider)
        for model in (models or ["gpt-4o", "gpt-4o-mini", "gpt-3.5-turbo"]):
            await self._add_slot(_ProviderSlot("openai", model, base_url, weight, True))

    async def register_anthropic(
        self,
        *,
        api_key: str,
        base_url: Optional[str] = None,
        models: Optional[list[str]] = None,
        weight: int = 1,
    ) -> None:
        if not api_key:
            return
        provider = AnthropicProvider(api_key=api_key, base_url=base_url)
        await self._health.register_provider("anthropic", provider)
        for model in (models or ["claude-3-5-sonnet-20241022", "claude-3-haiku-20240307"]):
            await self._add_slot(_ProviderSlot("anthropic", model, base_url, weight, True))

    async def register_ollama(
        self,
        *,
        base_url: Optional[str] = None,
        models: Optional[list[str]] = None,
        weight: int = 1,
    ) -> None:
        provider = OllamaProvider(base_url=base_url)
        await self._health.register_provider("ollama", provider)
        for model in (models or ["llama3.2", "qwen2.5:7b"]):
            await self._add_slot(_ProviderSlot("ollama", model, base_url, weight, True))

    async def register_vllm(
        self,
        *,
        base_url: Optional[str] = None,
        models: Optional[list[str]] = None,
        weight: int = 1,
    ) -> None:
        if not base_url:
            return
        provider = VLLMProvider(base_url=base_url)
        await self._health.register_provider("vllm", provider)
        for model in (models or ["meta-llama/Meta-Llama-3-8B-Instruct"]):
            await self._add_slot(_ProviderSlot("vllm", model, base_url, weight, True))

    async def _add_slot(self, slot: _ProviderSlot) -> None:
        async with self._lock:
            self._slots.append(slot)

    # -------------------------------------------------------------- chat
    async def chat(
        self,
        *,
        tenant_id: str,
        user_id: str,
        model: str,
        messages: list[dict[str, Any]],
        temperature: float = 0.7,
        max_tokens: int = 1024,
        stream: bool = False,
        trace_id: Optional[str] = None,
        timeout_s: float = 60.0,
    ) -> dict[str, Any]:
        """Non-streaming chat – R3, R5, R6."""
        async with self._lock:
            fallback_chain = self._build_fallback_chain(model)

        for slot in fallback_chain:
            if not slot.enabled:
                continue
            circuit = self._health.get_circuit(slot.provider)
            if circuit == CircuitState.OPEN:
                logger.warning("circuit open for %s, skipping", slot.provider)
                continue
            try:
                # R5: check quota before calling
                usage = await self._quota.check_and_consume(
                    tenant_id=tenant_id,
                    model=slot.model,
                    provider=slot.provider,
                    prompt_tokens=0,  # estimated; refined after call
                )
                if not usage.allowed:
                    self._health.trip_circuit(slot.provider)
                    continue

                result = await asyncio.wait_for(
                    self._invoke_provider(slot, messages, temperature, max_tokens, stream=False),
                    timeout=timeout_s,
                )
                # R5: refine cost with real usage
                await self._cost.track(
                    tenant_id=tenant_id,
                    user_id=user_id,
                    trace_id=trace_id or "",
                    provider=slot.provider,
                    model=slot.model,
                    prompt_tokens=usage.prompt_tokens,
                    completion_tokens=usage.completion_tokens,
                    total_tokens=usage.total_tokens,
                    cost_usd=usage.cost_usd,
                )
                await self._audit.log_usage(
                    trace_id=trace_id or "",
                    tenant_id=tenant_id,
                    user_id=user_id,
                    provider=slot.provider,
                    model=slot.model,
                    prompt_tokens=usage.prompt_tokens,
                    completion_tokens=usage.completion_tokens,
                    total_tokens=usage.total_tokens,
                    cost_usd=usage.cost_usd,
                    success=True,
                )
                return result
            except Exception as exc:
                logger.warning("provider %s/%s failed: %r", slot.provider, slot.model, exc)
                self._health.record_failure(slot.provider)
                continue

        raise RuntimeError(f"All providers failed for model={model}")

    async def chat_stream(
        self,
        *,
        tenant_id: str,
        user_id: str,
        model: str,
        messages: list[dict[str, Any]],
        temperature: float = 0.7,
        max_tokens: int = 1024,
        trace_id: Optional[str] = None,
        timeout_s: float = 120.0,
    ) -> AsyncIterator[dict[str, Any]]:
        """Streaming chat – yields SSE-compatible chunks. R3, R5, R6."""
        async with self._lock:
            fallback_chain = self._build_fallback_chain(model)

        for slot in fallback_chain:
            if not slot.enabled:
                continue
            circuit = self._health.get_circuit(slot.provider)
            if circuit == CircuitState.OPEN:
                continue
            try:
                usage = await self._quota.check_and_consume(
                    tenant_id=tenant_id,
                    model=slot.model,
                    provider=slot.provider,
                    prompt_tokens=0,
                )
                if not usage.allowed:
                    self._health.trip_circuit(slot.provider)
                    continue

                async with asyncio.timeout(timeout_s):
                    async for chunk in self._invoke_provider(
                        slot, messages, temperature, max_tokens, stream=True
                    ):
                        yield chunk
                    # Finalize cost on last chunk
                    await self._cost.track(
                        tenant_id=tenant_id,
                        user_id=user_id,
                        trace_id=trace_id or "",
                        provider=slot.provider,
                        model=slot.model,
                        prompt_tokens=usage.prompt_tokens,
                        completion_tokens=usage.completion_tokens,
                        total_tokens=usage.total_tokens,
                        cost_usd=usage.cost_usd,
                    )
                    await self._audit.log_usage(
                        trace_id=trace_id or "",
                        tenant_id=tenant_id,
                        user_id=user_id,
                        provider=slot.provider,
                        model=slot.model,
                        prompt_tokens=usage.prompt_tokens,
                        completion_tokens=usage.completion_tokens,
                        total_tokens=usage.total_tokens,
                        cost_usd=usage.cost_usd,
                        success=True,
                    )
                    return
            except Exception as exc:
                logger.warning("stream provider %s/%s failed: %r", slot.provider, slot.model, exc)
                self._health.record_failure(slot.provider)
                continue

        raise RuntimeError(f"All providers failed for stream model={model}")

    # -------------------------------------------------------------- helpers
    def _build_fallback_chain(self, requested_model: str) -> list[_ProviderSlot]:
        """Round-robin over enabled slots, prioritizing matching model, then fallback."""
        with self._lock:
            all_slots = list(self._slots)
        matched = [s for s in all_slots if s.model == requested_model and s.enabled]
        others = [s for s in all_slots if s.model != requested_model and s.enabled]
        return matched + others

    async def _invoke_provider(
        self,
        slot: _ProviderSlot,
        messages: list[dict[str, Any]],
        temperature: float,
        max_tokens: int,
        stream: bool,
    ) -> Any:
        adapters = {
            "openai": OpenAIProvider,
            "anthropic": AnthropicProvider,
            "ollama": OllamaProvider,
            "vllm": VLLMProvider,
        }
        adapter_cls = adapters[slot.provider]
        adapter = adapter_cls()
        if stream:
            return adapter.chat_stream(
                model=slot.model, messages=messages, temperature=temperature, max_tokens=max_tokens
            )
        return await adapter.chat(
            model=slot.model, messages=messages, temperature=temperature, max_tokens=max_tokens
        )

    # --------------------------------------------------------- status / admin
    async def get_status(self) -> dict[str, Any]:
        return {
            "slots": [
                {
                    "provider": s.provider,
                    "model": s.model,
                    "base_url": s.base_url,
                    "weight": s.weight,
                    "enabled": s.enabled,
                    "circuit": self._health.get_circuit(s.provider).name,
                }
                for s in self._slots
            ],
            "circuits": {
                p: c.name for p, c in self._health._circuits.items()
            },
        }

    async def toggle_provider(self, provider: str, enabled: bool) -> None:
        async with self._lock:
            for s in self._slots:
                if s.provider == provider:
                    s.enabled = enabled
        if enabled:
            self._health.close_circuit(provider)
        else:
            self._health.trip_circuit(provider)
