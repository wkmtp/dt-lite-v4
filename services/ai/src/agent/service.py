"""AI Agent Runtime — Agent definition, prompt template, tool allowlist, memory."""
from __future__ import annotations

import logging
import re
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)

AGENT_CODE_PATTERN = re.compile(r"^agent\.(park|factory)\.[a-z_][a-z0-9_]*$")
VALID_SAFETY_LEVELS = {"C0", "C1", "C2", "C3", "C4"}
SAFETY_LEVEL_ORDER = {"C0": 0, "C1": 1, "C2": 2, "C3": 3, "C4": 4}
VALID_MEMORY_TYPES = {"episodic", "semantic", "none"}


@dataclass
class AgentMemory:
    """Simple in-memory store for agent context."""
    entries: list[dict[str, Any]] = field(default_factory=list)
    max_entries: int = 100

    def add(self, entry: dict[str, Any]) -> None:
        self.entries.append(entry)
        if len(self.entries) > self.max_entries:
            self.entries = self.entries[-self.max_entries:]

    def get_recent(self, n: int = 10) -> list[dict[str, Any]]:
        return self.entries[-n:]


@dataclass
class Agent:
    """AI Agent definition.

    Key invariant: Agent MUST NOT have capability_code.
    Agents interact with capabilities ONLY through Tools.
    """
    id: str
    code: str
    name: str
    tool_allowlist: list[str] = field(default_factory=list)  # tool codes
    prompt_template: str = ""
    memory_config: dict[str, Any] = field(default_factory=dict)
    safety_level_max: str = "C2"
    owner_role: str = "ai_agent"
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def memory(self) -> AgentMemory:
        return self._memory

    def __post_init__(self) -> None:
        self._memory = AgentMemory()

    def check_safety(self, required_level: str) -> bool:
        """Check if agent can invoke a tool with given safety level."""
        return SAFETY_LEVEL_ORDER.get(self.safety_level_max, 0) >= SAFETY_LEVEL_ORDER.get(required_level, 0)


class AgentRuntime:
    """Agent runtime: CRUD, tool allowlist enforcement, memory management.

    Key invariant: Agent CANNOT directly hold capability_code.
    Agent can only invoke tools from its allowlist.
    """

    def __init__(self) -> None:
        self._agents: dict[str, Agent] = {}

    def create(self, data: dict[str, Any]) -> Agent:
        """Create an agent with validation."""
        for key in ["id", "code", "name"]:
            if key not in data:
                raise ValueError(f"Agent missing required field: {key}")

        # HARD RULE: Agent MUST NOT have capability_code
        if "capability_code" in data:
            raise ValueError(
                "Agent MUST NOT have capability_code field. "
                "Agents interact with capabilities only through Tools."
            )

        if not AGENT_CODE_PATTERN.match(data["code"]):
            raise ValueError(
                f"Agent code '{data['code']}' does not match convention: "
                f"agent.<domain>.<type>"
            )

        if data.get("safety_level_max", "C2") not in VALID_SAFETY_LEVELS:
            raise ValueError(
                f"Invalid safety_level_max '{data.get('safety_level_max')}'. "
                f"Must be one of: {sorted(VALID_SAFETY_LEVELS)}"
            )

        memory_config = data.get("memory_config", {"type": "episodic", "ttl_seconds": 3600, "max_entries": 100})
        if memory_config.get("type") not in VALID_MEMORY_TYPES:
            raise ValueError(
                f"Invalid memory_type '{memory_config.get('type')}'. "
                f"Must be one of: {sorted(VALID_MEMORY_TYPES)}"
            )

        agent = Agent(
            id=data["id"],
            code=data["code"],
            name=data["name"],
            tool_allowlist=data.get("tool_allowlist", []),
            prompt_template=data.get("prompt_template", ""),
            memory_config=memory_config,
            safety_level_max=data.get("safety_level_max", "C2"),
            owner_role=data.get("owner_role", "ai_agent"),
            metadata=data.get("metadata", {}),
        )
        self._agents[agent.id] = agent
        logger.info("Created agent: %s (%s) tools=%d safety_max=%s",
                     agent.id, agent.code, len(agent.tool_allowlist), agent.safety_level_max)
        return agent

    def get(self, agent_id: str) -> Optional[Agent]:
        return self._agents.get(agent_id)

    def can_invoke_tool(self, agent_id: str, tool_code: str) -> bool:
        """Check if agent has tool in allowlist."""
        agent = self._agents.get(agent_id)
        if not agent:
            return False
        return tool_code in agent.tool_allowlist

    def can_invoke_tool_safety(self, agent_id: str, tool_code: str, tool_safety_level: str) -> bool:
        """Check both allowlist AND safety level constraint."""
        if not self.can_invoke_tool(agent_id, tool_code):
            return False
        agent = self._agents.get(agent_id)
        if not agent:
            return False
        return agent.check_safety(tool_safety_level)

    def add_to_allowlist(self, agent_id: str, tool_code: str) -> Optional[Agent]:
        agent = self._agents.get(agent_id)
        if not agent:
            return None
        if tool_code not in agent.tool_allowlist:
            agent.tool_allowlist.append(tool_code)
        return agent

    def remove_from_allowlist(self, agent_id: str, tool_code: str) -> Optional[Agent]:
        agent = self._agents.get(agent_id)
        if not agent:
            return None
        if tool_code in agent.tool_allowlist:
            agent.tool_allowlist.remove(tool_code)
        return agent

    def record_memory(self, agent_id: str, entry: dict[str, Any]) -> bool:
        """Record a memory entry for an agent."""
        agent = self._agents.get(agent_id)
        if not agent:
            return False
        agent.memory.add(entry)
        return True

    def get_memory(self, agent_id: str, n: int = 10) -> list[dict[str, Any]]:
        agent = self._agents.get(agent_id)
        if not agent:
            return []
        return agent.memory.get_recent(n)

    def delete(self, agent_id: str) -> bool:
        if agent_id in self._agents:
            del self._agents[agent_id]
            return True
        return False
