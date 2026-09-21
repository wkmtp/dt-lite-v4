"""Permission Engine — RBAC + ABAC, resource-action-constraint."""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)

VALID_ACTIONS = {"read", "write", "execute", "approve", "administer"}
VALID_EFFECTS = {"allow", "deny"}


@dataclass
class RBACRule:
    """A role-based access control rule."""
    id: str
    role: str
    resource: str  # asset, point, alarm, tool, agent, permission, scene
    action: str
    description: str = ""


@dataclass
class ABACConstraint:
    """An attribute-based access control constraint."""
    id: str
    resource_type: str
    condition: str  # Jinja2-like: "category IN ['hvac'] AND tenant_id == '{{tenant_id}}'"
    effect: str = "allow"
    description: str = ""


class PermissionEngine:
    """Permission engine: RBAC + ABAC, deny-by-default.

    Every AI tool invocation MUST pass through this engine.
    No implicit permissions — explicitly granted or denied.
    """

    def __init__(self) -> None:
        self._rbac_rules: dict[str, RBACRule] = {}
        self._abac_constraints: dict[str, ABACConstraint] = {}

    def add_rbac_rule(self, data: dict[str, Any]) -> RBACRule:
        """Add an RBAC rule."""
        for key in ["role", "resource", "action"]:
            if key not in data:
                raise ValueError(f"RBAC rule missing required field: {key}")
        if data["action"] not in VALID_ACTIONS:
            raise ValueError(f"Invalid action '{data['action']}'. Must be one of: {sorted(VALID_ACTIONS)}")

        rule_id = str(uuid.uuid4())
        rule = RBACRule(
            id=rule_id,
            role=data["role"],
            resource=data["resource"],
            action=data["action"],
            description=data.get("description", ""),
        )
        self._rbac_rules[rule_id] = rule
        logger.info("Added RBAC rule: %s role=%s resource=%s action=%s", rule_id, rule.role, rule.resource, rule.action)
        return rule

    def add_abac_constraint(self, data: dict[str, Any]) -> ABACConstraint:
        """Add an ABAC constraint."""
        for key in ["resource_type", "condition", "effect"]:
            if key not in data:
                raise ValueError(f"ABAC constraint missing required field: {key}")
        if data["effect"] not in VALID_EFFECTS:
            raise ValueError(f"Invalid effect '{data['effect']}'. Must be: allow or deny")

        constraint_id = str(uuid.uuid4())
        constraint = ABACConstraint(
            id=constraint_id,
            resource_type=data["resource_type"],
            condition=data["condition"],
            effect=data["effect"],
            description=data.get("description", ""),
        )
        self._abac_constraints[constraint_id] = constraint
        return constraint

    def check(self, role: str, action: str, resource: str, context: dict[str, Any] | None = None) -> bool:
        """Check if a role-action-resource combination is permitted.

        Deny-by-default: if no rule matches, return False.
        ABAC constraints are evaluated after RBAC rules.
        """
        context = context or {}

        # Step 1: Check RBAC rules
        rbac_allowed = False
        rbac_denied = False
        for rule in self._rbac_rules.values():
            if rule.role == role and rule.action == action and rule.resource == resource:
                if rule.action == "administer":
                    rbac_allowed = True
                elif rule.action == action:
                    rbac_allowed = True

        # Step 2: Check ABAC constraints (deny overrides allow)
        abac_denied = False
        for constraint in self._abac_constraints.values():
            if constraint.resource_type == resource:
                # Simple condition evaluation (in production, use proper template engine)
                if self._evaluate_condition(constraint.condition, context):
                    if constraint.effect == "deny":
                        abac_denied = True
                    elif constraint.effect == "allow":
                        abac_allowed = True

        # Deny-by-default: ABAC deny wins, then explicit deny, then no match
        if abac_denied:
            return False
        if rbac_denied:
            return False
        return rbac_allowed

    def _evaluate_condition(self, condition: str, context: dict[str, Any]) -> bool:
        """Simple condition evaluator for ABAC constraints.

        Supports: IN, ==, !=, AND, OR, {{template_vars}}
        """
        import re
        # Replace template variables
        eval_condition = condition
        for key, value in context.items():
            eval_condition = re.sub(re.escape(f"{{{{{key}}}}}"), repr(value), eval_condition)

        # Handle IN clause
        if " IN " in eval_condition:
            parts = eval_condition.split(" IN ")
            if len(parts) == 2:
                field_name = parts[0].strip()
                try:
                    values = eval(parts[1].strip())
                    return context.get(field_name) in values
                except (NameError, SyntaxError):
                    pass

        # Handle equality
        if "==" in eval_condition:
            parts = eval_condition.split("==")
            if len(parts) == 2:
                field_name = parts[0].strip()
                try:
                    expected = eval(parts[1].strip())
                    return context.get(field_name) == expected
                except (NameError, SyntaxError):
                    pass

        # Default: if condition contains template vars, evaluate literally
        return eval_condition in str(context)

    def list_rbac_rules(self) -> list[RBACRule]:
        return list(self._rbac_rules.values())

    def list_abac_constraints(self) -> list[ABACConstraint]:
        return list(self._abac_constraints.values())

    def delete_rbac_rule(self, rule_id: str) -> bool:
        if rule_id in self._rbac_rules:
            del self._rbac_rules[rule_id]
            return True
        return False

    def delete_abac_constraint(self, constraint_id: str) -> bool:
        if constraint_id in self._abac_constraints:
            del self._abac_constraints[constraint_id]
            return True
        return False
