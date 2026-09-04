"""Deployment service exceptions."""


class DeploymentError(Exception):
    """Base exception for deployment operations."""

    def __init__(self, message: str, code: str = "DEPLOYMENT_ERROR"):
        self.message = message
        self.code = code
        super().__init__(self.message)


class ProfileNotFoundError(DeploymentError):
    """Deployment profile not found."""

    def __init__(self, profile_id):
        super().__init__(
            f"Deployment profile {profile_id} not found",
            code="PROFILE_NOT_FOUND",
        )


class InstanceNotFoundError(DeploymentError):
    """Deployment instance not found."""

    def __init__(self, instance_id):
        super().__init__(
            f"Deployment instance {instance_id} not found",
            code="INSTANCE_NOT_FOUND",
        )


class DuplicateCodeError(DeploymentError):
    """Duplicate code within tenant scope."""

    def __init__(self, resource_type: str, code: str):
        super().__init__(
            f"{resource_type} code '{code}' already exists for this tenant",
            code="DUPLICATE_CODE",
        )


class InvalidStatusTransitionError(DeploymentError):
    """Invalid status transition for deployment instance."""

    def __init__(self, current_status: str, target_status: str):
        super().__init__(
            f"Cannot transition from '{current_status}' to '{target_status}'",
            code="INVALID_STATUS_TRANSITION",
        )


class MissingCapabilityError(DeploymentError):
    """Required capability missing from deployment."""

    def __init__(self, capability_code: str, node_name: str):
        super().__init__(
            f"Required capability '{capability_code}' missing on node '{node_name}'",
            code="MISSING_CAPABILITY",
        )
