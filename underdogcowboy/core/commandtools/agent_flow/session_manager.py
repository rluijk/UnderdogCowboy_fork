import logging
from uccli import StateMachine, StorageManager

class SessionManager:
    """Handles loading, creating, and saving sessions."""
    
    def __init__(self, storage_manager: StorageManager):
        self.storage_manager = storage_manager
        self.current_storage = None  # Holds the current session storage
    
    def load_session(self, session_name: str):
        try:
            self.current_storage = self.storage_manager.load_session(session_name)
            logging.info(f"Session '{session_name}' loaded successfully.")
            return self.current_storage
        except ValueError as e:
            logging.error(f"Error loading session '{session_name}': {str(e)}")
            raise

    def create_session(self, session_name: str):
        try:
            self.current_storage = self.storage_manager.create_session(session_name)
            logging.info(f"Session '{session_name}' created successfully.")
            return self.current_storage
        except ValueError as e:
            logging.error(f"Error creating session '{session_name}': {str(e)}")
            raise

    def save_current_session(self):
        if self.current_storage:
            self.storage_manager.save_current_session(self.current_storage)
            logging.info(f"Current session saved successfully.")
        else:
            logging.warning("No session to save.")

    def get_current_state(self):
        if self.current_storage:
            return self.current_storage.get_data("current_state")
        else:
            logging.warning("No current session loaded.")
            return None

    def update_session_state(self, new_state: str):
        if self.current_storage:
            self.current_storage.update_data("current_state", new_state)
            self.save_current_session()
            logging.info(f"Session state updated to '{new_state}'.")
        else:
            logging.warning("No session loaded to update state.")
