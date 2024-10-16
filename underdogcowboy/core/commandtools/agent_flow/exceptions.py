class ApplicationError(Exception):
    """Base class for all custom exceptions in the application."""
    pass


class AnalysisError(ApplicationError):
    """Base class for analysis-related errors."""
    pass


""" Session related """
class SessionError(ApplicationError):
    """Base class for session-related errors."""
    pass

class SessionNotLoadedError(SessionError):
    """Raised when an operation is attempted without an active session."""
    pass

class SessionAlreadyExistsError(SessionError):
    """Raised when attempting to create a session that already exists."""
    pass

class SessionDoesNotExistError(SessionError):
    """Raised when attempting to load a non-existent session."""
    pass

class InvalidSessionDataError(SessionError):
    """Raised when the session data is invalid or corrupted."""
    pass

""" Event related """

# related exception for connecting code (ours) to the Textual Libraries even driven system.
class MessagePostTargetNotSetError(Exception):
    """Exception raised when message post target is not set."""
    pass



""" Storage related """
class StorageError(ApplicationError):
    """Base class for storage-related errors."""
    pass

class StorageInitializationError(StorageError):
    """Raised when the storage system fails to initialize."""
    pass

class StorageOperationError(StorageError):
    """Raised when a storage operation fails."""
    pass


""" Screen related """
class ScreenError(ApplicationError):
    """Base class for screen-related errors."""
    pass

class ScreenDataError(ScreenError):
    """Raised when there's an issue with screen-specific data."""
    pass


""" Statemachine related """
class StateMachineError(ApplicationError):
    """Base class for state machine errors."""
    pass

class InvalidStateTransitionError(StateMachineError):
    """Raised when an invalid state transition is attempted."""
    pass

class StateNotFoundError(StateMachineError):
    """Raised when a state is not found in the state machine."""
    pass
