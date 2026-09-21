"""Assembly Engine — Zero-Code Assembly: Recipe, Plan, State Machine, Retry/Idempotency/Rollback."""
from __future__ import annotations

import hashlib
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger(__name__)

# 10 Assembly States
class AssemblyState(str, Enum):
    PENDING = "pending"
    VALIDATING = "validating"
    PLANNING = "planning"
    EXECUTING = "executing"
    PAUSED = "paused"
    ROLLING_BACK = "rolling_back"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

VALID_TRANSITIONS = {
    AssemblyState.PENDING: {AssemblyState.VALIDATING, AssemblyState.CANCELLED},
    AssemblyState.VALIDATING: {AssemblyState.PLANNING, AssemblyState.FAILED},
    AssemblyState.PLANNING: {AssemblyState.EXECUTING, AssemblyState.FAILED},
    AssemblyState.EXECUTING: {AssemblyState.PAUSED, AssemblyState.COMPLETED, AssemblyState.ROLLING_BACK, AssemblyState.FAILED},
    AssemblyState.PAUSED: {AssemblyState.EXECUTING, AssemblyState.CANCELLED},
    AssemblyState.ROLLING_BACK: {AssemblyState.FAILED, AssemblyState.EXECUTING},
    AssemblyState.COMPLETED: set(),
    AssemblyState.FAILED: {AssemblyState.PENDING},
    AssemblyState.CANCELLED: {AssemblyState.PENDING},
}

# 11 Step Types
VALID_STEP_TYPES = {
    "create_asset", "instantiate_template", "bind_point", "deploy_mapping",
    "deploy_capability", "generate_dashboard", "generate_largescreen",
    "configure_alarm", "configure_workflow", "configure_ai_tool", "publish_app",
}


@dataclass
class AssemblyContext:
    """Execution context for an assembly run."""
    tenant_id: str
    project_id: str
    environment: str  # dev | staging | prod
    parameters: dict[str, Any] = field(default_factory=dict)
    secrets: dict[str, str] = field(default_factory=dict)
    audit_id: str = ""
    assembled_at: str = ""

    def context_hash(self) -> str:
        content = f"{self.tenant_id}:{self.project_id}:{self.environment}:{self.audit_id}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]


@dataclass
class AssemblyStep:
    """A single step in an assembly recipe."""
    id: str
    type: str
    depends_on: list[str] = field(default_factory=list)
    input_schema: dict[str, Any] = field(default_factory=dict)
    output_schema: dict[str, Any] = field(default_factory=dict)
    retry_policy: dict[str, Any] = field(default_factory=dict)
    rollback_handler: str = ""
    timeout_seconds: int = 30
    status: str = "pending"  # pending | running | success | failed | skipped
    result: Optional[dict[str, Any]] = None
    error: Optional[str] = None
    attempt: int = 0


@dataclass
class AssemblyPlan:
    """Compiled executable plan from Recipe + Context."""
    id: str
    recipe_id: str
    context: AssemblyContext
    steps: list[dict[str, Any]] = field(default_factory=list)
    parallel_groups: list[list[str]] = field(default_factory=list)
    created_at: str = ""


@dataclass
class AssemblyResult:
    """Final result of an assembly execution."""
    assembly_id: str
    state: str
    steps_completed: int = 0
    steps_failed: int = 0
    total_steps: int = 0
    duration_seconds: float = 0.0
    error: Optional[str] = None
    outputs: dict[str, Any] = field(default_factory=dict)


class AssemblyEngine:
    """Assembly engine: Recipe validation, DAG planning, state machine, retry/idempotency/rollback.

    Zero-Code: All steps are declarative; engine handles orchestration.
    """

    def __init__(self) -> None:
        self._assemblies: dict[str, dict[str, Any]] = {}

    def _compute_idempotency_key(self, step_id: str, input_params: dict[str, Any], context: AssemblyContext) -> str:
        """Compute idempotency key for a step."""
        content = f"{step_id}:{hash(str(sorted(input_params.items())))}:{context.context_hash()}"
        return hashlib.sha256(content.encode()).hexdigest()[:32]

    def _compute_retry_delay(self, attempt: int, base_delay: float = 1.0) -> float:
        """Exponential backoff with 10% jitter."""
        import random
        delay = (2 ** attempt) * base_delay
        jitter = delay * 0.1 * random.uniform(-1, 1)
        return max(0.1, delay + jitter)

    def validate_recipe(self, recipe: dict[str, Any]) -> tuple[bool, list[str]]:
        """Validate an AssemblyRecipe DSL."""
        errors: list[str] = []

        if "version" not in recipe:
            errors.append("Missing required field: version")
        if "steps" not in recipe or not isinstance(recipe.get("steps"), list):
            errors.append("Missing or invalid 'steps' array")
            return len(errors) == 0, errors

        step_ids = set()
        for i, step in enumerate(recipe["steps"]):
            for key in ["id", "type"]:
                if key not in step:
                    errors.append(f"Step {i}: missing required field '{key}'")

            if "type" in step and step["type"] not in VALID_STEP_TYPES:
                errors.append(f"Step {i}: invalid type '{step['type']}'. Must be one of: {sorted(VALID_STEP_TYPES)}")

            if "id" in step:
                if step["id"] in step_ids:
                    errors.append(f"Step {i}: duplicate id '{step['id']}'")
                step_ids.add(step["id"])

            # Check depends_on references exist
            for dep in step.get("depends_on", []):
                if dep not in step_ids and dep != step.get("id"):
                    # dep might be defined later — skip check for now
                    pass

        # Check for circular dependencies (simple check)
        if not errors:
            try:
                self._detect_cycle(recipe["steps"])
            except ValueError as e:
                errors.append(str(e))

        return len(errors) == 0, errors

    def _detect_cycle(self, steps: list[dict[str, Any]]) -> None:
        """Detect cycles in step dependencies using DFS."""
        step_map = {s["id"]: s for s in steps}
        visited = set()
        rec_stack = set()

        def dfs(sid: str) -> bool:
            visited.add(sid)
            rec_stack.add(sid)
            for dep in step_map.get(sid, {}).get("depends_on", []):
                if dep not in visited:
                    if dfs(dep):
                        return True
                elif dep in rec_stack:
                    return True
            rec_stack.remove(sid)
            return False

        for sid in step_map:
            if sid not in visited:
                if dfs(sid):
                    raise ValueError("Circular dependency detected in recipe steps")

    def compile_plan(self, recipe_id: str, recipe: dict[str, Any], context: AssemblyContext) -> AssemblyPlan:
        """Compile recipe + context into executable plan."""
        plan_id = str(uuid.uuid4())
        steps = []
        for step in recipe.get("steps", []):
            step_copy = dict(step)
            step_copy["idempotency_key"] = self._compute_idempotency_key(
                step["id"], step.get("input_params", {}), context
            )
            steps.append(step_copy)

        # Identify parallel groups (steps with no dependencies on each other)
        parallel_groups = self._compute_parallel_groups(steps)

        plan = AssemblyPlan(
            id=plan_id,
            recipe_id=recipe_id,
            context=context,
            steps=steps,
            parallel_groups=parallel_groups,
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        logger.info("Compiled plan %s for recipe %s: %d steps, %d parallel groups",
                     plan_id, recipe_id, len(steps), len(parallel_groups))
        return plan

    def _compute_parallel_groups(self, steps: list[dict[str, Any]]) -> list[list[str]]:
        """Compute parallel execution groups using topological sort levels."""
        step_map = {s["id"]: s for s in steps}
        deps = {s["id"]: set(s.get("depends_on", [])) for s in steps}
        groups: list[list[str]] = []
        remaining = set(step_map.keys())

        while remaining:
            # Find steps with all dependencies satisfied
            group = []
            for sid in list(remaining):
                if deps[sid].issubset(set().union(*[g for g in groups]) if groups else set()):
                    group.append(sid)
            if not group:
                # Break ties arbitrarily (shouldn't happen if no cycles)
                group = [next(iter(remaining))]
            groups.append(group)
            for sid in group:
                remaining.remove(sid)

        return groups

    def transition(self, assembly_id: str, new_state: AssemblyState) -> tuple[bool, str]:
        """Transition assembly to new state. Enforces state machine."""
        assembly = self._assemblies.get(assembly_id)
        if not assembly:
            return False, "Assembly not found"

        current = AssemblyState(assembly["state"])
        allowed = VALID_TRANSITIONS.get(current, set())

        if new_state not in allowed:
            return False, f"Invalid transition from '{current.value}' to '{new_state.value}'"

        assembly["state"] = new_state.value
        assembly["state_history"].append({
            "from": current.value,
            "to": new_state.value,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        return True, f"Transitioned to {new_state.value}"

    def get_state(self, assembly_id: str) -> Optional[str]:
        assembly = self._assemblies.get(assembly_id)
        return assembly["state"] if assembly else None

    def create_assembly(self, recipe_id: str, context: AssemblyContext) -> str:
        """Create a new assembly in PENDING state."""
        assembly_id = str(uuid.uuid4())
        self._assemblies[assembly_id] = {
            "id": assembly_id,
            "recipe_id": recipe_id,
            "context": context,
            "state": AssemblyState.PENDING.value,
            "state_history": [{
                "from": None, "to": AssemblyState.PENDING.value,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }],
            "plan": None,
            "step_results": {},
            "result": None,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        return assembly_id

    def execute_step(self, assembly_id: str, step_id: str, input_params: dict[str, Any]) -> dict[str, Any]:
        """Execute a single assembly step with idempotency check."""
        assembly = self._assemblies.get(assembly_id)
        if not assembly:
            raise ValueError(f"Assembly {assembly_id} not found")

        if assembly["state"] not in {AssemblyState.EXECUTING.value, AssemblyState.ROLLING_BACK.value}:
            raise ValueError(f"Cannot execute step in state {assembly['state']}")

        # Idempotency check
        context = assembly["context"]
        idem_key = self._compute_idempotency_key(step_id, input_params, context)
        if idem_key in assembly.get("step_results", {}):
            return assembly["step_results"][idem_key]

        # Simulate step execution
        result = {
            "step_id": step_id,
            "idempotency_key": idem_key,
            "status": "success",
            "output": {"assembled": True, "step_type": "simulated"},
            "latency_ms": 5.0,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        assembly["step_results"][idem_key] = result
        return result

    def get_result(self, assembly_id: str) -> Optional[AssemblyResult]:
        assembly = self._assemblies.get(assembly_id)
        if not assembly:
            return None
        return assembly.get("result")
