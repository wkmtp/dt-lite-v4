"""Template service exceptions."""


class TemplateError(Exception):
    """Base exception for template operations."""

    def __init__(self, message: str, code: str = "TEMPLATE_ERROR"):
        self.message = message
        self.code = code
        super().__init__(self.message)


class TemplateNotFoundError(TemplateError):
    """Template not found."""

    def __init__(self, template_id):
        super().__init__(
            f"Template {template_id} not found",
            code="TEMPLATE_NOT_FOUND",
        )


class DuplicateCodeError(TemplateError):
    """Duplicate template code within tenant."""

    def __init__(self, code: str):
        super().__init__(
            f"Template code '{code}' already exists for this tenant",
            code="DUPLICATE_CODE",
        )


class InvalidSchemaError(TemplateError):
    """Invalid schema definition."""

    def __init__(self, message: str):
        super().__init__(message, code="INVALID_SCHEMA")


class TemplateDeletedError(TemplateError):
    """Attempted operation on deleted template."""

    def __init__(self, template_id):
        super().__init__(
            f"Template {template_id} has been deleted",
            code="TEMPLATE_DELETED",
        )
