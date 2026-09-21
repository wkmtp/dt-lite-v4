"""Base Agent ABC and ToolCallingAgent implementation.

Provides a unified interface for OpenAI Function Calling and
Anthropic Tool Use patterns through a vendor-agnostic abstraction.
All agents require tenant_id for isolation.
"""
from __future__ import annotations

import asyncio
import json
import logging
from abc import ABC, abstractmethod
from typing import Any, AsyncIterator, Literal, Optional

from pydantic import BaseModel, Field

from services.ai.config import AIConfig, get_ai_config

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Pydantic Schemas
# ---------------------------------------------------------------------------

class ToolDefinition(BaseModel):
    """Unified tool definition supporting both OpenAI and Anthropic formats."""

    name: str = Field(..., description="Tool name, must be unique within the registry")
    description: str = Field(..., description="Tool description for the LLM")
    input_schema: dict[str, Any] = Field(
        default_factory=dict,
        description="JSON Schema describing the tool input parameters",
    )
    vendor_format: Literal["openai", "anthropic"] = Field(
        default="openai",
        description="The vendor format this definition targets",
    )


class AgentMessage(BaseModel):
    """A single message in the agent conversation history."""

    role: Literal["system", "user", "assistant", "tool"] = Field(..., description="Message role")
    content: str = Field(..., description="Message text content")
    tool_calls: Optional[list[dict[str, Any]]] = Field(
        None,
        description="Tool call requests (OpenAI format) or tool_use blocks (Anthropic format)",
    )
    tool_result: Optional[dict[str, Any]] = Field(
        None,
        description="Tool execution result",
    )


class ToolCallResult(BaseModel):
    """Result of executing a single tool call."""

    tool_name: str
    tool_input: dict[str, Any]
    tool_output: Any
    success: bool
    error_message: Optional[str] = None


class AgentResponse(BaseModel):
    """Unified response from an agent run."""

    final_message: str = Field(..., description="The agent's final text response")
    tool_calls_executed: list[ToolCallResult] = Field(
        default_factory=list,
        description="All tool calls made during execution",
    )
    iterations: int = Field(default=0, description="Number of ReAct iterations performed")
    stopped_early: bool = Field(default=False, description="Whether the loop stopped before max iterations")


# ---------------------------------------------------------------------------
# Base Agent ABC
# ---------------------------------------------------------------------------

class BaseAgent(ABC):
    """Abstract base class for all DT-Lite AI agents.

    Subclasses must implement ``run()`` and ``run_streaming()``.
    All subclasses are tenant-scoped — the ``tenant_id`` is used to
    isolate data access across organisations.
    """

    def __init__(
        self,
        tenant_id: str,
        config: Optional[AIConfig] = None,
    ) -> None:
        self.tenant_id: str = tenant_id
        self.config: AIConfig = config or get_ai_config()
        self._messages: list[AgentMessage] = []

    @property
    @abstractmethod
    def agent_type(self) -> str:
        """Return a human-readable agent type identifier."""

    @abstractmethod
    async def run(self, user_prompt: str, **kwargs: Any) -> AgentResponse:
        """Run the agent synchronously and return the final response.

        Args:
            user_prompt: The user's request text.
            **kwargs: Additional runtime parameters.

        Returns:
            AgentResponse with the final message and call history.
        """

    @abstractmethod
    async def run_streaming(
        self,
        user_prompt: str,
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        """Run the agent with SSE streaming output.

        Yields text chunks as they are produced.

        Args:
            user_prompt: The user's request text.
            **kwargs: Additional runtime parameters.
        """

    def _append_message(self, message: AgentMessage) -> None:
        """Thread-safe append to conversation history."""
        self._messages.append(message)

    def _get_messages(self) -> list[dict[str, Any]]:
        """Convert internal messages to a list of dicts for LLM consumption."""
        return [
            {
                "role": msg.role,
                "content": msg.content,
                **({k: v for k, v in {"tool_calls": msg.tool_calls, "tool_result": msg.tool_result}.items() if v is not None},),
            }
            for msg in self._messages
        ]


# ---------------------------------------------------------------------------
# ToolCallingAgent — unified OpenAI / Anthropic interface
# ---------------------------------------------------------------------------

class ToolCallingAgent(BaseAgent):
    """Agent that uses LLM function/tool calling to decide which tools to invoke.

    Supports both OpenAI Function Calling and Anthropic Tool Use through a
    single unified interface. The underlying provider is selected via
    ``AIConfig.llm_provider``.
    """

    def __init__(
        self,
        tenant_id: str,
        tools: list[ToolDefinition],
        system_prompt: str,
        config: Optional[AIConfig] = None,
        max_iterations: int = 10,
    ) -> None:
        super().__init__(tenant_id, config)
        self._tools: list[ToolDefinition] = tools
        self._system_prompt = system_prompt
        self._max_iterations = max_iterations
        self._tool_handlers: dict[str, Any] = {}

    @property
    def agent_type(self) -> str:
        return "tool_calling"

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def run(self, user_prompt: str, **kwargs: Any) -> AgentResponse:
        """Execute the agent loop and return the final response."""
        self._messages.clear()
        self._messages.append(AgentMessage(role="system", content=self._system_prompt))
        self._messages.append(AgentMessage(role="user", content=user_prompt))

        response = AgentResponse(
            final_message="",
            iterations=0,
            stopped_early=False,
        )

        for _ in range(self._max_iterations):
            llm_response = await self._call_llm(self._get_messages())
            if not llm_response.tool_calls:
                response.final_message = llm_response.content
                break

            tool_results = await self._execute_tool_calls(llm_response.tool_calls)
            self._messages.append(AgentMessage(
                role="assistant",
                content="",
                tool_calls=llm_response.tool_calls,
            ))
            for tc_result in tool_results:
                self._messages.append(AgentMessage(
                    role="tool",
                    content=json.dumps(tc_result.tool_output, default=str),
                    tool_result=tc_result.tool_output,
                ))
                response.tool_calls_executed.append(tc_result)

            response.iterations += 1
        else:
            response.stopped_early = True
            response.final_message = (
                "[Agent stopped] Maximum iterations reached without a final answer."
            )

        return response

    async def run_streaming(
        self,
        user_prompt: str,
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        """Execute the agent loop with SSE-style token streaming."""
        self._messages.clear()
        self._messages.append(AgentMessage(role="system", content=self._system_prompt))
        self._messages.append(AgentMessage(role="user", content=user_prompt))

        for _ in range(self._max_iterations):
            stream_chunks = await self._call_llm_stream(self._get_messages())
            full_content = ""
            async for chunk in stream_chunks:
                full_content += chunk
                yield chunk

            if not full_content.strip():
                continue

            # After receiving full content, check if tools need to be called
            llm_response = await self._call_llm(self._get_messages() + [
                {"role": "assistant", "content": full_content}
            ])
            if not llm_response.tool_calls:
                self._messages.append(AgentMessage(role="assistant", content=full_content))
                break

            tool_results = await self._execute_tool_calls(llm_response.tool_calls)
            self._messages.append(AgentMessage(
                role="assistant",
                content=full_content,
                tool_calls=llm_response.tool_calls,
            ))
            for tc_result in tool_results:
                self._messages.append(AgentMessage(
                    role="tool",
                    content=json.dumps(tc_result.tool_output, default=str),
                    tool_result=tc_result.tool_output,
                ))

        yield "\n[Agent completed]"

    # ------------------------------------------------------------------
    # Tool Management
    # ------------------------------------------------------------------

    def register_tool(self, name: str, handler: Any) -> None:
        """Register a tool handler by name."""
        self._tool_handlers[name] = handler

    def unregister_tool(self, name: str) -> bool:
        """Remove a registered tool handler. Returns True if found."""
        return self._tool_handlers.pop(name, None) is not None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _execute_tool_calls(
        self,
        tool_calls: list[dict[str, Any]],
    ) -> list[ToolCallResult]:
        """Execute a batch of tool calls and return their results."""
        results: list[ToolCallResult] = []
        for tc in tool_calls:
            tool_name = tc.get("name", "")
            try:
                tool_input = json.loads(tc.get("arguments", "{}"))
            except json.JSONDecodeError:
                tool_input = {}

            handler = self._tool_handlers.get(tool_name)
            if handler is None:
                results.append(ToolCallResult(
                    tool_name=tool_name,
                    tool_input=tool_input,
                    tool_output=None,
                    success=False,
                    error_message=f"Tool '{tool_name}' not found",
                ))
                continue

            try:
                if asyncio.iscoroutinefunction(handler):
                    output = await handler(**tool_input)
                else:
                    output = handler(**tool_input)
                results.append(ToolCallResult(
                    tool_name=tool_name,
                    tool_input=tool_input,
                    tool_output=output,
                    success=True,
                ))
            except Exception as exc:
                logger.warning("Tool %s execution failed: %s", tool_name, exc, exc_info=True)
                results.append(ToolCallResult(
                    tool_name=tool_name,
                    tool_input=tool_input,
                    tool_output=None,
                    success=False,
                    error_message=str(exc),
                ))
        return results

    @abstractmethod
    async def _call_llm(self, messages: list[dict[str, Any]]) -> AgentMessage:
        """Call the LLM provider and return a structured message.

        Must be implemented by subclasses to support OpenAI / Anthropic.
        """

    @abstractmethod
    async def _call_llm_stream(
        self,
        messages: list[dict[str, Any]],
    ) -> AsyncIterator[str]:
        """Call the LLM provider with streaming and yield text chunks.

        Must be implemented by subclasses.
        """
