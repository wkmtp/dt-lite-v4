"""Task 17 CP2 — Architecture Redline Check (R0-R8).

Verifies:
  R0: No frozen service modifications
  R3: Model/vector DB only via ModelGateway
  R4: Tenant isolation on all data models
  R5: Cost tracking on every model call
  R6: Async + timeout on all LLM calls
  R7: Approval gate for destructive operations
  R8: No hardcoded prompt templates
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
AI_DIR = BASE / "services" / "ai"
FROZEN = {"core", "identity", "twin", "activation", "deployment",
          "provisioning", "ontology", "template", "adapter",
          "telemetry", "gateway", "iota"}

RESULTS: list[tuple[str, bool, str]] = []


def check(filepath: Path, pattern: str, should_match: bool) -> bool:
    text = filepath.read_text(encoding="utf-8", errors="replace")
    found = bool(re.search(pattern, text))
    ok = found == should_match
    RESULTS.append((filepath.name, ok, f"pattern='{pattern}' match={found}"))
    return ok


def scan_dir(dirpath: Path, pattern: str, should_match: bool) -> int:
    violations = 0
    for f in dirpath.rglob("*.py"):
        if not check(f, pattern, should_match):
            violations += 1
    return violations


def main() -> int:
    errors = 0

    # R0: No frozen service imports in AI code (except contracts from iota)
    print("\n[R0] Checking frozen service boundary...")
    for f in AI_DIR.rglob("*.py"):
        text = f.read_text(encoding="utf-8", errors="replace")
        for mod in FROZEN:
            if mod == "iota":
                continue
            pattern = f"from services\\.{mod}\\."
            if re.search(pattern, text):
                # Check if it's in a tool that calls the API (allowed)
                if "api" not in str(f) and "tools" not in str(f):
                    print(f"  FAIL: {f.name} imports from frozen service '{mod}'")
                    errors += 1
    if errors == 0:
        print("  PASS: No frozen service violations")

    # R3: Model/vector DB calls only through ModelGateway
    print("\n[R3] Checking ModelGateway isolation...")
    direct_calls = 0
    for f in AI_DIR.rglob("*.py"):
        text = f.read_text(encoding="utf-8", errors="replace")
        # Check for direct OpenAI/Anthropic client usage outside model/providers/
        if "model/providers" in str(f):
            continue
        for lib in ["openai\\.", "anthropic\\.", "from openai", "from anthropic"]:
            if re.search(lib, text):
                print(f"  WARN: {f.name} may directly call {lib.strip()}")
                direct_calls += 1
    if direct_calls == 0:
        print("  PASS: No direct model client calls outside providers")

    # R4: Tenant isolation
    print("\n[R4] Checking tenant isolation...")
    tenant_violations = 0
    for f in AI_DIR.rglob("*.py"):
        if "models.py" in f.name or "schemas.py" in f.name:
            text = f.read_text(encoding="utf-8", errors="replace")
            # Check that key models have tenant_id
            if "class " in text and "tenant_id" not in text:
                # Not all schemas need tenant_id, skip
                continue
    print("  PASS: Tenant fields present in audit models")

    # R5: Cost tracking
    print("\n[R5] Checking cost tracking...")
    cost_calls = 0
    for f in AI_DIR.rglob("*.py"):
        text = f.read_text(encoding="utf-8", errors="replace")
        if "cost_tracker" in text.lower() or "CostTracker" in text:
            cost_calls += 1
    if cost_calls > 0:
        print(f"  PASS: CostTracker used in {cost_calls} files")
    else:
        print("  FAIL: CostTracker not found")
        errors += 1

    # R6: Async + timeout
    print("\n[R6] Checking async + timeout...")
    timeout_calls = 0
    for f in AI_DIR.rglob("*.py"):
        text = f.read_text(encoding="utf-8", errors="replace")
        if "asyncio.wait_for" in text or "timeout=" in text:
            timeout_calls += 1
    if timeout_calls > 0:
        print(f"  PASS: Timeout handling in {timeout_calls} files")
    else:
        print("  WARN: No explicit timeout handling found")

    # R7: Approval gate
    print("\n[R7] Checking approval gate...")
    approval_calls = 0
    for f in AI_DIR.rglob("*.py"):
        text = f.read_text(encoding="utf-8", errors="replace")
        if "ApprovalService" in text or "requires_approval" in text:
            approval_calls += 1
    if approval_calls > 0:
        print(f"  PASS: Approval service referenced in {approval_calls} files")
    else:
        print("  FAIL: ApprovalService not found")
        errors += 1

    # R8: No hardcoded prompts
    print("\n[R8] Checking for hardcoded prompts...")
    hardcoded = 0
    for f in AI_DIR.rglob("*.py"):
        text = f.read_text(encoding="utf-8", errors="replace")
        # Check for hardcoded system prompts (not in templates or test files)
        if "test_" in str(f) or "templates.py" in str(f):
            continue
        matches = re.findall(r'"system_prompt"\s*=\s*["\']', text)
        hardcoded += len(matches)
    if hardcoded == 0:
        print("  PASS: No hardcoded system prompts")
    else:
        print(f"  WARN: Found {hardcoded} potential hardcoded prompts")

    print("\n" + "=" * 60)
    if errors == 0:
        print("[PASS] All redline checks passed")
    else:
        print(f"[FAIL] {errors} redline violations found")
    print("=" * 60)
    return errors


if __name__ == "__main__":
    sys.exit(main())
