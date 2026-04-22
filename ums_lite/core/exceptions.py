class UMSCoreException(Exception):
    """Base exception for all UMS domain exceptions."""
    pass

class EntityNotFoundError(UMSCoreException):
    """Raised when a requested entity cannot be found in the datastore."""
    pass

class DuplicateEntityError(UMSCoreException):
    """Raised when attempting to create an entity that already exists (e.g., unique constraint violation)."""
    pass

class InvalidStateError(UMSCoreException):
    """Raised when an action is attempted on an entity in an invalid state."""
    pass
