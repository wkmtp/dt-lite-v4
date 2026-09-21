"""Test architecture compliance for activation layer."""
from pathlib import Path
import re


class TestArchitectureScan:
    """Verify services/activation has zero forbidden imports."""

    FORBIDDEN_IMPORTS = [
        "services.adapter",
        "services.telemetry",
        "services.adapter.*",
        "services.telemetry.*",
        "services.bacnet",
        "services.modbus",
        "services.mqtt",
        "services.opcua",
        "services.plc",
        "services.ai",
        "services.kafka",
        "services.redis",
    ]

    FORBIDDEN_KEYWORDS = [
        "bacnet", "modbus", "mqtt", "opcua", "plc",
        "kafka", "redis", "celery",
    ]

    def test_no_forbidden_imports(self):
        """Scan all Python files in services/activation/ for forbidden imports."""
        source_dir = Path("services/activation")
        for py_file in source_dir.rglob("*.py"):
            content = py_file.read_text(encoding="utf-8")
            for forbidden in self.FORBIDDEN_IMPORTS:
                pattern = rf'from\s+{re.escape(forbidden)}|import\s+{re.escape(forbidden.split(".")[-1])}'
                matches = re.findall(pattern, content)
                assert not matches, f"Forbidden import '{forbidden}' found in {py_file}"

    def test_no_protocol_keywords(self):
        """No protocol-specific keywords in activation source."""
        source_dir = Path("services/activation")
        for py_file in source_dir.rglob("*.py"):
            content = py_file.read_text(encoding="utf-8")
            stripped = re.sub(r'#.*$', '', content, flags=re.MULTILINE)
            for keyword in self.FORBIDDEN_KEYWORDS:
                assert not re.search(r'\b' + keyword + r'\b', stripped), \
                    f"Forbidden keyword '{keyword}' found in {py_file}"

    def test_migration_chain_correct(self):
        """Migration must extend phase13_provisioning."""
        migration_path = Path("database/migrations/versions")
        for py_file in migration_path.rglob("phase14*.py"):
            content = py_file.read_text(encoding="utf-8")
            assert "phase13_provisioning" in content, \
                f"Migration {py_file} must extend phase13_provisioning"

    def test_gateway_integrates_activation_router(self):
        """Gateway must include activation router."""
        main_path = Path("services/gateway/main.py")
        content = main_path.read_text(encoding="utf-8")
        assert "activation" in content, "Gateway must import activation router"
        assert "activation_router" in content, "Gateway must include activation_router"


class TestNoNewBindingModel:
    """Verify activation does not create a new TwinBinding model."""

    def test_no_duplicate_binding_model(self):
        """Activation must not define a model with tablename 'twin_bindings'."""
        from services.activation.models import TwinActivationLog, TwinCommand
        assert TwinActivationLog.__tablename__ != "twin_bindings"
        assert TwinCommand.__tablename__ != "twin_bindings"

    def test_existing_binding_reused(self):
        """Existing TwinBinding from Task 9 must be reusable."""
        from services.twin.models.binding import TwinBinding
        assert TwinBinding.__tablename__ == "twin_bindings"
        # Verify it has the expected fields
        annotations = TwinBinding.__annotations__
        assert "tenant_id" in annotations
        assert "device_id" in annotations
        assert "twin_entity_id" in annotations
