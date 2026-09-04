"""Permission-related exceptions."""
from services.exceptions.base import PermissionDenied


class InsufficientPermissions(PermissionDenied):
    """User lacks required permissions."""

    def __init__(self, required_permissions: list[str], user_id: str = ""):
        super().__init__(
            permission_code=", ".join(required_permissions),
            user_id=user_id or None
        )
        self.message = f"Insufficient permissions. Required: {required_permissions}"
        self.code = "INSUFFICIENT_PERMISSIONS"
        self.required_permissions = required_permissions
