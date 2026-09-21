"""ReAct Loop: Thought → Action → Observation cycle.

Implements the classic ReAct pattern where the agent:
  1. Thinks about what to do next.
  2. Picks an action (tool call).
  3. Observes the result.
  4. Repeats until a final answer is reached or max iterations expire.

Supports early stopping via ``stop_condition`` callbacks.
"""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Awaitable, Callable, Optional

from pydantic import BaseModel, Field

from services.ai.agent.base import AgentResponse, BaseAgent, ToolCallResult
from services.ai.agent.memory import MemoryManager
from services.ai.config import AIConfig, get_ai_config

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class ReActStep(BaseModel):
    """One iteration of the ReAct loop."""

    step_index: int = Field(..., description="1-based step number")
    thought: str = Field(..., description="The agent's reasoning at this step")
    action: Optional[str] = Field(None, description="Tool name invoked")
    action_input: dict[str, Any] = Field(
        default_factory=dict,
        description="Arguments passed to the tool",
    )
    observation: Optional[str] = Field(None, description="Tool output as string")
    is_final: bool = Field(default=False, description="True if this step produced the final answer")


class ReActResult(BaseModel):
    """Complete result of a ReAct loop execution."""

    steps: list[ReActStep] = Field(default_factory=list)
    final_answer: str = Field(..., description="The agent's concluding response")
    total_iterations: int = Field(default=0, description="Number of loop iterations")
    stopped_early: bool = Field(default=False, description="Whether a stop condition triggered")
    early_stop_reason: Optional[str] = None


# ---------------------------------------------------------------------------
# ReActLoop
# ---------------------------------------------------------------------------

class ReActLoop:
    """Implements the Thought → Action → Observation ReAct cycle.

    Args:
        base_agent: The underlying agent that handles LLM calls.
        max_iterations: Hard cap on loop rounds (default 10).
        timeout_seconds: Per-iteration timeout.
        stop_conditions: Optional list of async predicates that can terminate early.
    """

    def __init__(
        self,
        base_agent: BaseAgent,
        max_iterations: int = 10,
        timeout_seconds: int = 120,
        stop_conditions: Optional[list[Callable[[ReActResult], Awaitable[bool]]]] = None,
    ) -> None:
        self._agent = base_agent
        self._max_iterations = max_iterations
        self._timeout = timeout_seconds
        self._stop_conditions = stop_conditions or []
        self._memory = MemoryManager(
            tenant_id=base_agent.tenant_id,
            config=base_agent.config,
        )

    async def run(self, user_prompt: str) -> ReActResult:
        """Execute the full ReAct loop and return the result."""
        result = ReActResult()
        self._memory.clear_short_term()
        self._memory.add_to_short_term("user", user_prompt)

        for step_idx in range(1, self._max_iterations + 1):
            # Check stop conditions before each iteration
            for cond in self._stop_conditions:
                if await cond(result):
                    result.stopped_early = True
                    result.early_stop_reason = "custom_stop_condition"
                    return result

            step = await self._run_step(step_idx, user_prompt)
            result.steps.append(step)
            result.total_iterations = step_idx

            self._memory.add_to_short_term("assistant", step.thought)
            if step.observation:
                self._memory.add_to_short_term("observation", step.observation)

            if step.action and step.observation:
                self._memory.set_working(f"action_{step_idx}", step.observation)

            if step.is_final:
                result.final_answer = step.thought
                return result

        # Max iterations reached
        result.stopped_early = True
        result.early_stop_reason = "max_iterations"
        result.final_answer = (
            "[ReAct] Reached maximum iterations without a final answer."
        )
        return result

    async def run_with_memory(
        self,
        user_prompt: str,
        previous_context: Optional[dict[str, Any]] = None,
    ) -> ReActResult:
        """Run ReAct loop restoring relevant long-term memories first."""
        if previous_context:
            for key, value in previous_context.items():
                self._memory.set_working(key, value)

        relevant_memories = await self._memory.search_long_term(
            query=user_prompt,
            top_k=3,
        )
        if relevant_memories:
            context_block = "\n".join(
                f"[Memory {i+1}] {m.content}"
                for i, m in enumerate(relevant_memories)
            )
            user_prompt = f"{context_block}\n\n{user_prompt}"

        return await self.run(user_prompt)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    async def _run_step(
        self,
        step_idx: int,
        user_prompt: str,
    ) -> ReActStep:
        """Execute a single ReAct iteration."""
        messages = self._memory.get_short_term()

        thought_action = await asyncio.wait_for(
            self._agent.run(
                user_prompt=user_prompt,
                _internal_messages=messages,
            ),
            timeout=self._timeout,
        )

        # Determine if this is the final step or an action step
        if not thought_action.tool_calls_executed:
            return ReActStep(
                step_index=step_idx,
                thought=thought_action.final_message,
                is_final=True,
            )

        tc = thought_action.tool_calls_executed[0]
        return ReActStep(
            step_index=step_idx,
            thought=thought_action.final_message,
            action=tc.tool_name,
            action_input=tc.tool_input,
            observation=json.dumps(tc.tool_output, default=str) if tc.tool_output else None,
            is_final=False,
        )
