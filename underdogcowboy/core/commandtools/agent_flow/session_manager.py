import os
import logging
import datetime
from typing import Any, List, Dict
from state_management.storage_interface import StorageInterface
from state_management.shared_data import SessionData, ScreenData
from underdogcowboy.core.config_manager import LLMConfigManager
# Events / Mixins
from events.message_mixin import MessageEmitterMixin

# Sessions
from events.session_events import SessionStateChanged

from exceptions import (
    SessionNotLoadedError,
    ScreenDataError,
    StorageOperationError,
    SessionDoesNotExistError
)

import platform

class SessionManager(MessageEmitterMixin):
    """Handles loading, creating, and saving sessions using the storage abstraction layer."""
    
    def __init__(self, storage: StorageInterface):
        super().__init__()  # Initialize the mixin
        self.storage = storage
        self.current_session_name: str = None
        self.current_session_data: SessionData = None  # Holds the current session data
        self.config_manager: LLMConfigManager = LLMConfigManager()

    def create_session(self, session_name: str):
        """
        Create a new session and initialize its folder within the project path.

        Args:
            session_name (str): The name of the session to create.

        Raises:
            ValueError: If session creation fails.
        """
        try:
            # Retrieve the project path from the config manager
            project_path = self.config_manager.get_general_config().get("project_path")
            if not project_path:
                raise ValueError("Project path is not configured. Please set it in the general configuration.")

            # Ensure the project path exists
            os.makedirs(project_path, exist_ok=True)

            # Create a folder for the session
            session_folder = os.path.join(project_path, session_name)
            os.makedirs(session_folder, exist_ok=True)

            # Create the session in the storage layer
            self.current_session_data = self.storage.create_session(session_name)
            self.current_session_name = session_name

            logging.info(f"Session '{session_name}' created successfully at '{session_folder}'.")
            self.post_message(SessionStateChanged(self, session_active=True, session_name=session_name))

        except ValueError as e:
            logging.error(f"Error creating session '{session_name}': {str(e)}")
            raise

        except OSError as e:
            logging.error(f"Filesystem error creating session folder '{session_name}': {str(e)}")
            raise

    def load_session(self, session_name: str):
        """
        Load an existing session and ensure its folder exists in the project path.

        Args:
            session_name (str): The name of the session to load.

        Raises:
            SessionDoesNotExistError: If the session does not exist in storage.
            StorageOperationError: If an error occurs during storage operations.
        """
        try:
            # Load session data from storage
            self.current_session_data = self.storage.load_session(session_name)
            self.current_session_name = session_name

            # Retrieve the project path from the config manager
            project_path = self.config_manager.get_general_config().get("project_path")
            if not project_path:
                raise ValueError("Project path is not configured. Please set it in the general configuration.")

            # Ensure the session folder exists
            session_folder = os.path.join(project_path, session_name)
            if not os.path.exists(session_folder):
                os.makedirs(session_folder, exist_ok=True)
                logging.info(f"Session folder '{session_folder}' was missing and has been created.")

            logging.info(f"Session '{session_name}' loaded successfully.")
            self.post_message(SessionStateChanged(self, session_active=True, session_name=session_name))

        except SessionDoesNotExistError as e:
            logging.error(str(e))
            raise
        except StorageOperationError as e:
            logging.error(str(e))
            raise
        except OSError as e:
            logging.error(f"Filesystem error when checking/creating session folder for '{session_name}': {str(e)}")
            raise
        except Exception as e:
            logging.error(f"Unexpected error when loading session '{session_name}': {str(e)}")
            raise StorageOperationError(f"Failed to load session '{session_name}'") from e


    def __bck__create_session(self, session_name: str):
        try:
            self.current_session_data = self.storage.create_session(session_name)
            self.current_session_name = session_name
            logging.info(f"Session '{session_name}' created successfully.")
            self.post_message(SessionStateChanged(self, session_active=True, session_name=session_name))

        except ValueError as e:
            logging.error(f"Error creating session '{session_name}': {str(e)}")
            raise

    def __bck__load_session(self, session_name: str):
        try:
            
            self.current_session_data = self.storage.load_session(session_name)
            self.current_session_name = session_name
            logging.info(f"Session '{session_name}' loaded successfully.")
            self.post_message(SessionStateChanged(self, session_active=True, session_name=session_name))

        except SessionDoesNotExistError as e:
            logging.error(str(e))
            raise
        except StorageOperationError as e:
            logging.error(str(e))
            raise
        except Exception as e:
            logging.error(f"Unexpected error when loading session '{session_name}': {str(e)}")
            raise StorageOperationError(f"Failed to load session '{session_name}'") from e
    
    def save_current_session(self):
        if self.current_session_data and self.current_session_name:
            self.storage.save_session(self.current_session_name, self.current_session_data)
            logging.info("Current session saved successfully.")
        else:
            logging.warning("No session to save.")

    def list_sessions(self) -> List[str]:
        return self.storage.list_sessions()

    def get_data(self, key: str, screen_name: str = None) -> Any:
        if not self.current_session_data:
            logging.warning("No current session loaded.")
            return None
        if screen_name:
            screen_data = self.current_session_data.screens.get(screen_name)
            if screen_data:
                # agent on key here?
                return screen_data.data.get(key)
            else:
                return None
        else:
            return self.current_session_data.shared_data.data.get(key)

    def update_data(self, key: str, value: Any, screen_name: str = None) -> None:
        logging.info(f"Entering update_data method. Key: {key}, Value: {value}, Screen name: {screen_name}")
        
        if not self.current_session_data:
            logging.error("No current session loaded. Cannot update data.")
            raise SessionNotLoadedError("No active session loaded. Cannot update data.")
        
        logging.info(f"Current session data: {self.current_session_data}")
        
        try:
            if screen_name:
                logging.info(f"Updating screen-specific data for screen: {screen_name}")
                if screen_name not in self.current_session_data.screens:
                    logging.info(f"Creating new ScreenData for screen: {screen_name}")
                    self.current_session_data.screens[screen_name] = ScreenData()
                # agent on here aswell i think right?    
                self.current_session_data.screens[screen_name].data[key] = value
                logging.info(f"Updated screen-specific data.")
                # Log command
                command_desc = f"update_data: {key}"
                self.add_command_result(command_desc, {"value": value}, screen_name=screen_name)
            else:
                logging.info("Updating shared data")
                self.current_session_data.shared_data.data[key] = value
                logging.info(f"Updated shared data. New value:")
                # Log command
                command_desc = f"update_data: {key}"
                self.add_command_result(command_desc, {"value": value})
            # Save session after updating
            self.save_current_session()
            logging.info("Session saved after updating data")
        except KeyError as e:
            logging.error(f"Screen '{screen_name}' does not exist in session data.")
            raise ScreenDataError(f"Screen '{screen_name}' does not exist.") from e
        except Exception as e:
            logging.error(f"Error updating data: {str(e)}")
            logging.error(f"Exception type: {type(e)}")
            logging.error(f"Exception args: {e.args}")
            raise StorageOperationError("Failed to update data in the session.") from e

        logging.info("Exiting update_data method")


    def add_command_result(self, command: str, result: Any, screen_name: str = None) -> None:
        if not self.current_session_data:
            logging.warning("No current session loaded.")
            return
        command_entry = {
            "command": command,
            "result": result,
            "timestamp": datetime.datetime.now().isoformat()
        }
        if screen_name:
            if screen_name not in self.current_session_data.screens:
                self.current_session_data.screens[screen_name] = ScreenData()
            self.current_session_data.screens[screen_name].command_history.append(command_entry)
        else:
            self.current_session_data.shared_data.command_history.append(command_entry)
        # Save session after logging command
        self.save_current_session()

    def get_command_history(self, screen_name: str = None) -> List[Dict[str, Any]]:
        if not self.current_session_data:
            logging.warning("No current session loaded.")
            return []
        if screen_name:
            screen_data = self.current_session_data.screens.get(screen_name)
            if screen_data:
                return screen_data.command_history
            else:
                return []
        else:
            return self.current_session_data.shared_data.command_history
