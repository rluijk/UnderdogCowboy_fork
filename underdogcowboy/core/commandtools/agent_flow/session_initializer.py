from state_management.storage_interface import StorageInterface
from state_management.json_storage_manager import JSONStorageManager
from session_manager import SessionManager

def initialize_shared_session_manager(base_dir: str = "~/.tui_agent_clarity_03") -> SessionManager:
    """
    Initialize and return a shared SessionManager instance.

    Args:
        base_dir (str): The base directory for storage. Defaults to "~/.tui_agent_clarity_03".

    Returns:
        SessionManager: A shared session manager instance.
    """
    storage_interface: StorageInterface = JSONStorageManager(base_dir=base_dir)
    shared_session_manager = SessionManager(storage_interface)
    return shared_session_manager