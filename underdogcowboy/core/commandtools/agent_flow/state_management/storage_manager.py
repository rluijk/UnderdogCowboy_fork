
import os
from typing import Any, Dict, List
from state_management.shared_storage import SharedStorage
from exceptions import (SessionAlreadyExistsError, StorageOperationError, 
                        SessionDoesNotExistError, SessionNotLoadedError)

class StorageManager:
    def __init__(self, base_dir: str = ".agent_flow_sessions"):
        self.base_dir = os.path.expanduser(base_dir)
        self.current_session = None
        self.shared_storage = None  # Instance of SharedStorage
        self.ensure_base_dir()

    def ensure_base_dir(self):
        os.makedirs(self.base_dir, exist_ok=True)

    def create_session(self, name: str) -> SharedStorage:
        session_path = os.path.join(self.base_dir, f"{name}.json")
        
        # Check if the session file already exists
        if os.path.exists(session_path):
            raise SessionAlreadyExistsError(f"Session '{name}' already exists")
        
        storage = SharedStorage()
        
        try:
            # Attempt to save the new session file
            storage.save_to_file(session_path)
        except IOError as e:
            # Chain the original IOError and raise a custom storage error
            raise StorageOperationError(f"Failed to save session '{name}'") from e

        # Set the current session
        self.current_session = name
        self.shared_storage = storage
        
        return storage

    def load_session(self, name: str) -> SharedStorage:
        session_path = os.path.join(self.base_dir, f"{name}.json")
        if not os.path.exists(session_path):
            raise SessionDoesNotExistError(f"Session '{name}' does not exist")
        self.current_session = name
        self.shared_storage = SharedStorage.load_from_file(session_path)
        return self.shared_storage

    def load_session(self, name: str) -> SharedStorage:
        session_path = os.path.join(self.base_dir, f"{name}.json")
        
        # Raise a specific exception if the session doesn't exist.
        if not os.path.exists(session_path):
            raise SessionDoesNotExistError(f"Session '{name}' does not exist")
        
        # Continue with loading the session if it exists.
        self.current_session = name
        self.shared_storage = SharedStorage.load_from_file(session_path)
        return self.shared_storage

    def save_current_session(self):
        if not self.current_session:
            raise SessionNotLoadedError("No active session")
        session_path = os.path.join(self.base_dir, f"{self.current_session}.json")
        self.shared_storage.save_to_file(session_path)

    def list_sessions(self) -> List[str]:
        return [f.replace('.json', '') for f in os.listdir(self.base_dir) if f.endswith('.json')]

    # Updated methods to handle screen-specific data
    def update_data(self, key: str, value: Any, screen_name: str = None) -> None:
        if not self.shared_storage:
            raise ValueError("No active session")
        self.shared_storage.update_data(key, value, screen_name=screen_name)
        # Automatically log the data update to the command history
        command_desc = f"update_data: {key}"
        self.shared_storage.add_command_result(command_desc, {"value": value}, screen_name=screen_name)
        # Save the session after updating
        self.save_current_session()

    def get_data(self, key: str, screen_name: str = None) -> Any:
        if not self.shared_storage:
            raise SessionNotLoadedError("No active session")
        return self.shared_storage.get_data(key, screen_name=screen_name)

    def add_command_result(self, command: str, result: Any, screen_name: str = None) -> None:
        if not self.shared_storage:
            raise SessionNotLoadedError("No active session")
        self.shared_storage.add_command_result(command, result, screen_name=screen_name)
        self.save_current_session()

    def get_command_history(self, screen_name: str = None) -> List[Dict[str, Any]]:
        if not self.shared_storage:
            raise SessionNotLoadedError("No active session")
        if screen_name:
            screen_data = self.shared_storage.session_data.screens.get(screen_name)
            if screen_data:
                return screen_data.command_history
            else:
                return []
        else:
            return self.shared_storage.session_data.shared_data.command_history
