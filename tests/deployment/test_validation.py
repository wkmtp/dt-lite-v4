"""Test deployment schema validation."""
import pytest
from uuid import uuid4

from services.deployment.schemas import (
    DeploymentInstanceCreateRequest,
    DeploymentProfileCreateRequest,
    DeploymentNodeCreateRequest,
    DeploymentNodeCapabilityBindRequest,
)


class TestDeploymentProfileValidation:
    """Test DeploymentProfileCreateRequest validation."""

    def test_valid_profile(self):
        """Valid profile creation request."""
        req = DeploymentProfileCreateRequest(
            name="Smart Building",
            industry="general",
            template_id=uuid4(),
        )
        assert req.name == "Smart Building"

    def test_empty_name_rejected(self):
        """Empty profile name rejected."""
        with pytest.raises(Exception):
            DeploymentProfileCreateRequest(name="", industry="general", template_id=uuid4())

    def test_industry_lowercase(self):
        """Industry field lowercased."""
        req = DeploymentProfileCreateRequest(name="Test", industry="GENERAL", template_id=uuid4())
        assert req.industry == "general"


class TestDeploymentInstanceValidation:
    """Test DeploymentInstanceCreateRequest validation."""

    def test_valid_instance(self):
        """Valid instance creation request."""
        req = DeploymentInstanceCreateRequest(
            profile_id=uuid4(),
            name="My Instance",
        )
        assert req.status == "draft"

    def test_custom_status_accepted(self):
        """Custom valid status accepted."""
        req = DeploymentInstanceCreateRequest(
            profile_id=uuid4(),
            name="My Instance",
            status="ready",
        )
        assert req.status == "ready"

    def test_invalid_status_rejected(self):
        """Invalid status pattern rejected."""
        with pytest.raises(Exception):
            DeploymentInstanceCreateRequest(
                profile_id=uuid4(),
                name="Test",
                status="invalid_status",
            )

    def test_empty_name_rejected(self):
        """Empty instance name rejected."""
        with pytest.raises(Exception):
            DeploymentInstanceCreateRequest(profile_id=uuid4(), name="")


class TestDeploymentNodeValidation:
    """Test DeploymentNodeCreateRequest validation."""

    def test_valid_node(self):
        """Valid node creation request."""
        req = DeploymentNodeCreateRequest(
            name="AHU Room 101",
            node_type="room",
        )
        assert req.node_type == "room"

    def test_default_node_type(self):
        """Default node type is generic."""
        req = DeploymentNodeCreateRequest(name="Generic Node")
        assert req.node_type == "generic"

    def test_empty_name_rejected(self):
        """Empty node name rejected."""
        with pytest.raises(Exception):
            DeploymentNodeCreateRequest(name="")


class TestDeploymentNodeCapabilityValidation:
    """Test DeploymentNodeCapabilityBindRequest validation."""

    def test_valid_binding(self):
        """Valid capability binding."""
        req = DeploymentNodeCapabilityBindRequest(
            capability_id=uuid4(),
            configuration_schema={"param": "value"},
        )
        assert req.required is True

    def test_optional_config_schema(self):
        """Empty config schema allowed."""
        req = DeploymentNodeCapabilityBindRequest(capability_id=uuid4())
        assert req.configuration_schema == {}

    def test_required_field_can_be_false(self):
        """Optional capability binding."""
        req = DeploymentNodeCapabilityBindRequest(
            capability_id=uuid4(),
            required=False,
        )
        assert req.required is False
