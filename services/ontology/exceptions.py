"""Ontology service exceptions."""


class OntologyError(Exception):
    """Base exception for ontology operations."""

    def __init__(self, message: str, code: str = "ONTOLOGY_ERROR"):
        self.message = message
        self.code = code
        super().__init__(self.message)


class ConceptNotFoundError(OntologyError):
    """Ontology concept not found."""

    def __init__(self, concept_id):
        super().__init__(
            f"Ontology concept {concept_id} not found",
            code="CONCEPT_NOT_FOUND",
        )


class EntityTypeNotFoundError(OntologyError):
    """Entity type definition not found."""

    def __init__(self, entity_type_id):
        super().__init__(
            f"Entity type {entity_type_id} not found",
            code="ENTITY_TYPE_NOT_FOUND",
        )


class CapabilityNotFoundError(OntologyError):
    """Capability definition not found."""

    def __init__(self, capability_id):
        super().__init__(
            f"Capability {capability_id} not found",
            code="CAPABILITY_NOT_FOUND",
        )


class DuplicateCodeError(OntologyError):
    """Duplicate code within tenant scope."""

    def __init__(self, resource_type: str, code: str):
        super().__init__(
            f"{resource_type} code '{code}' already exists for this tenant",
            code="DUPLICATE_CODE",
        )


class InvalidSchemaError(OntologyError):
    """Invalid schema definition."""

    def __init__(self, message: str):
        super().__init__(message, code="INVALID_SCHEMA")


class CircularReferenceError(OntologyError):
    """Circular reference detected in ontology hierarchy."""

    def __init__(self, concept_id, ancestor_id):
        super().__init__(
            f"Circular reference: concept {concept_id} cannot be its own ancestor ({ancestor_id})",
            code="CIRCULAR_REFERENCE",
        )


class ParentNotfoundError(OntologyError):
    """Parent concept does not exist."""

    def __init__(self, parent_id):
        super().__init__(
            f"Parent concept {parent_id} not found",
            code="PARENT_NOT_FOUND",
        )
