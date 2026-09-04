"""TwinGraph exceptions."""


class TwinGraphError(Exception):
    """Base exception for twin graph operations."""

    def __init__(self, message: str, code: str = "TWIN_GRAPH_ERROR"):
        self.message = message
        self.code = code
        super().__init__(self.message)


class TwinRelationshipNotFoundError(TwinGraphError):
    """Relationship not found."""

    def __init__(self, relationship_id):
        super().__init__(
            f"Relationship {relationship_id} not found",
            code="TWIN_RELATIONSHIP_NOT_FOUND",
        )


class TwinEntityNotFoundError(TwinGraphError):
    """Twin entity not found."""

    def __init__(self, entity_id):
        super().__init__(
            f"Twin entity {entity_id} not found",
            code="TWIN_ENTITY_NOT_FOUND",
        )


class InvalidRelationshipError(TwinGraphError):
    """Invalid relationship (e.g., source == target)."""

    def __init__(self, message: str):
        super().__init__(message, code="INVALID_RELATIONSHIP")


class CycleDetectedError(TwinGraphError):
    """Cycle detected during path traversal."""

    def __init__(self, entity_id):
        super().__init__(
            f"Cycle detected at entity {entity_id}",
            code="CYCLE_DETECTED",
        )
