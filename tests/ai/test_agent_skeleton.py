"""Task 17 CP1 — Agent Runtime skeleton smoke test."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from services.ai.config import AIConfig
from services.ai.agent.base import BaseAgent, ToolCallingAgent
from services.ai.agent.memory import MemoryManager
from services.ai.agent.planner import TaskPlanner
from services.ai.agent.reactor import ReActLoop


class TestAgentBase:
    def test_config_loads(self):
        cfg = AIConfig()
        assert cfg.openai_model == "gpt-4o"
        assert cfg.agent_max_iterations == 10

    def test_base_agent_is_abc(self):
        with pytest.raises(TypeError):
            BaseAgent()  # abstract


class TestToolCallingAgent:
    @pytest.mark.asyncio
    async def test_agent_create(self):
        agent = ToolCallingAgent(
            tenant_id=uuid4(),
            user_id=uuid4(),
            model="gpt-4o",
        )
        assert agent.tenant_id is not None
        assert agent.model == "gpt-4o"


class TestMemoryManager:
    def test_memory_manager_init(self):
        mm = MemoryManager(tenant_id=uuid4())
        assert mm.tenant_id is not None


class TestTaskPlanner:
    def test_planner_init(self):
        planner = TaskPlanner()
        assert planner is not None


class TestReActLoop:
    def test_react_init(self):
        loop = ReActLoop(max_iterations=5)
        assert loop.max_iterations == 5

    @pytest.mark.asyncio
    async def test_react_step_structure(self):
        loop = ReActLoop(max_iterations=2)
        # Verify it has the expected interface
        assert hasattr(loop, "run")
        assert hasattr(loop, "step")
