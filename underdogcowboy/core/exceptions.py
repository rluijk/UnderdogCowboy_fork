class AgentInitializationError(Exception):
    """Raised when an agent cannot be properly initialized or registered."""

class ModelConfigurationError(Exception):
    """Raised when the model configuration or initialization fails."""

class AgentNotPreparedError(Exception):
    """Raised when attempting to use an agent that has not been prepared."""

class InvalidAgentError(Exception):
    """Raised when an invalid agent instance or type is provided."""

class InterventionModeError(Exception):
    """Raised when an error occurs in activating or deactivating intervention mode."""

class DialogNotFoundError(Exception):
    """Raised when a requested dialog file cannot be found."""

class InvalidProcessorError(Exception):
    """Raised when an invalid CommandProcessor is provided."""