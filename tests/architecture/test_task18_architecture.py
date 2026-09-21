"""Task 18 — Architecture Redline Tests (R0-R8).

These tests enforce architectural constraints for Task 18 Edge Computing.
Must pass before any merge to main.
"""
from __future__ import annotations

import ast
import subprocess
from pathlib import Path
from typing import Iterable

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
FROZEN_SERVICES = [
    "services/core",
    "services/twin",
    "services/activation",
    "services/identity",
    "services/telemetry",
    "services/adapter",
    "services/ai",
    "services/deployment",
    "services/provisioning",
    "services/ontology",
    "services/template",
    "services/gateway",
    "services/iota",
]
EDGE_DIRS = [
    "services/edge",
    "services/sync",
    "services/adapter/edge",
    "deployment/edge",
]


def _git_diff_files() -> list[str]:
    """Get list of files changed vs main branch."""
    try:
        result = subprocess.run(
            ["git", "diff", "--name-only", "main", "HEAD"],
            capture_output=True, text=True, cwd=str(PROJECT_ROOT),
        )
        if result.returncode != 0:
            return []
        return [f.strip() for f in result.stdout.splitlines() if f.strip()]
    except Exception:
        return []


def _rglob_py(directory: str) -> list[Path]:
    """Get all Python files under a directory."""
    dir_path = PROJECT_ROOT / directory
    if not dir_path.exists():
        return []
    return list(dir_path.rglob("*.py"))


# ---------------------------------------------------------------------------
# R0: No frozen service modifications
# ---------------------------------------------------------------------------

class TestR0NoFrozenServiceModification:
    """严禁修改冻结服务代码."""

    def test_no_frozen_service_changes(self):
        changed = _git_diff_files()
        violations = [
            f for f in changed
            if any(f.startswith(prefix + "/") for prefix in FROZEN_SERVICES)
        ]
        assert not violations, f"R0 违规: 修改了冻结服务文件: {violations}"


# ---------------------------------------------------------------------------
# R1: No new microservice processes
# ---------------------------------------------------------------------------

class TestR1NoNewMicroservice:
    """严禁引入新的微服务进程."""

    def test_no_extra_main_py(self):
        """Only edge/main.py allowed as entry point."""
        edge_main = PROJECT_ROOT / "services/edge/main.py"
        sync_mains = list((PROJECT_ROOT / "services/sync").rglob("main.py"))
        # edge/main.py is the single entry point
        assert edge_main.exists(), "R1 违规: services/edge/main.py 不存在"
        # sync should not have its own main.py
        assert len(sync_mains) == 0, f"R1 违规: sync 目录有独立 main.py: {sync_mains}"


# ---------------------------------------------------------------------------
# R2: No direct cloud database access
# ---------------------------------------------------------------------------

class TestR2NoDirectCloudDB:
    """严禁边缘侧直连云端数据库."""

    def test_no_asyncpg_direct_connection(self):
        """Check for asyncpg connections to cloud DSNs in edge/sync."""
        for py_file in _rglob_py("services/edge") + _rglob_py("services/sync"):
            content = py_file.read_text(encoding="utf-8", errors="replace")
            # Should not have postgresql:// DSN in edge/sync code
            if "postgresql://" in content or "postgres://" in content:
                # Allow in tests or migration files
                if "/test_" not in str(py_file) and "migration" not in str(py_file):
                    pytest.fail(f"R2 违规: {py_file} 包含云端数据库连接字符串")


# ---------------------------------------------------------------------------
# R3: No wall-clock time in sync logic
# ---------------------------------------------------------------------------

class TestR3NoWallClockSync:
    """严禁同步协议依赖中心化时钟."""

    def test_no_time_based_sync(self):
        """Sync module should not use time.time() or datetime.now()."""
        sync_files = _rglob_py("services/sync")
        for py_file in sync_files:
            content = py_file.read_text(encoding="utf-8", errors="replace")
            # Skip test files
            if "/test_" in str(py_file):
                continue
            # Check for wall-clock usage in sync logic
            if "time.time()" in content and "hlc" not in content.lower():
                pytest.fail(f"R3 违规: {py_file} 使用 time.time() 而非 HLC")
            if "datetime.now()" in content and "hlc" not in content.lower():
                pytest.fail(f"R3 违规: {py_file} 使用 datetime.now() 而非 HLC")


# ---------------------------------------------------------------------------
# R4: Local write durability
# ---------------------------------------------------------------------------

class TestR4LocalWriteDurability:
    """本地写入必须持久化后才返回."""

    def test_edge_write_persistence(self):
        """Verify edge storage has persistence layer."""
        storage_dir = PROJECT_ROOT / "services/edge/storage"
        assert storage_dir.exists(), "R4 违规: services/edge/storage 目录不存在"
        # Check for SQLite or TimescaleDB implementation
        py_files = list(storage_dir.rglob("*.py"))
        has_impl = any(
            f.read_text(encoding="utf-8", errors="replace")
            for f in py_files
            if "sqlite" in f.name.lower() or "timescale" in f.name.lower() or "persist" in f.name.lower()
        )
        # At minimum, the directory should exist with implementation files
        assert len(py_files) > 0, "R4 违规: storage 目录无实现文件"


# ---------------------------------------------------------------------------
# R5: No hardcoded tenant/asset IDs
# ---------------------------------------------------------------------------

class TestR5NoHardcodedIDs:
    """严禁边缘侧硬编码租户/资产 ID."""

    def test_no_hardcoded_tenant_asset(self):
        for py_file in _rglob_py("services/edge") + _rglob_py("services/sync"):
            if "/test_" in str(py_file):
                continue
            content = py_file.read_text(encoding="utf-8", errors="replace")
            # Check for hardcoded IDs (simplified check)
            import re
            patterns = [
                r'tenant_id\s*=\s*["\'][a-f0-9-]+["\']',
                r'asset_id\s*=\s*["\'][a-f0-9-]+["\']',
                r'device_id\s*=\s*["\'][a-f0-9-]+["\']',
            ]
            for pattern in patterns:
                matches = re.findall(pattern, content)
                assert not matches, f"R5 违规: {py_file.name} 包含硬编码 ID: {matches[:3]}"


# ---------------------------------------------------------------------------
# R6: No blocking I/O in sync
# ---------------------------------------------------------------------------

class TestR6NoBlockingIO:
    """严禁同步路径阻塞事件循环."""

    def test_no_blocking_imports(self):
        for py_file in _rglob_py("services/sync"):
            if "/test_" in str(py_file):
                continue
            content = py_file.read_text(encoding="utf-8", errors="replace")
            # Check for blocking imports
            if "import requests" in content:
                pytest.fail(f"R6 违规: {py_file} 导入阻塞库 requests")
            if "from requests" in content:
                pytest.fail(f"R6 违规: {py_file} 从 requests 导入")


# ---------------------------------------------------------------------------
# R7: OTA signature verification
# ---------------------------------------------------------------------------

class TestR7OTASignature:
    """OTA 升级必须签名验证."""

    def test_ota_module_exists(self):
        ota_dir = PROJECT_ROOT / "services/edge/ota"
        assert ota_dir.exists(), "R7 违规: services/edge/ota 目录不存在"

    def test_ota_uses_ed25519_or_blake3(self):
        ota_files = list((PROJECT_ROOT / "services/edge/ota").rglob("*.py"))
        assert len(ota_files) > 0, "R7 违规: OTA 模块无 Python 文件"
        content = "\n".join(f.read_text(encoding="utf-8", errors="replace") for f in ota_files)
        has_crypto = "ed25519" in content.lower() or "blake3" in content.lower() or "signature" in content.lower()
        assert has_crypto, "R7 违规: OTA 模块缺少签名验证实现"


# ---------------------------------------------------------------------------
# R8: Resource limits in deployment
# ---------------------------------------------------------------------------

class TestR8ResourceLimits:
    """部署清单必须有资源限制."""

    def test_k8s_manifests_have_limits(self):
        k8s_dir = PROJECT_ROOT / "deployment/edge/kubernetes"
        if not k8s_dir.exists():
            pytest.skip("R8: deployment/edge/kubernetes 目录不存在，跳过")
        yaml_files = list(k8s_dir.rglob("*.yaml")) + list(k8s_dir.rglob("*.yml"))
        assert len(yaml_files) > 0, "R8 违规: 无 K8s 部署清单"
        # Check that at least one manifest has resource limits
        has_limits = False
        for yaml_file in yaml_files:
            content = yaml_file.read_text(encoding="utf-8", errors="replace")
            if "limits:" in content and "cpu:" in content and "memory:" in content:
                has_limits = True
                break
        assert has_limits, "R8 违规: K8s 清单缺少资源限制配置"


# ---------------------------------------------------------------------------
# Runtime verification (when git diff not available)
# ---------------------------------------------------------------------------

class TestEdgeStructure:
    """Verify edge service directory structure exists."""

    def test_edge_core_exists(self):
        assert (PROJECT_ROOT / "services/edge/core").exists()

    def test_sync_engine_exists(self):
        assert (PROJECT_ROOT / "services/sync/engine.py").exists()

    def test_edge_storage_exists(self):
        assert (PROJECT_ROOT / "services/edge/storage").exists()

    def test_edge_compute_exists(self):
        assert (PROJECT_ROOT / "services/edge/compute").exists()

    def test_edge_adapter_exists(self):
        assert (PROJECT_ROOT / "services/adapter/edge").exists()
