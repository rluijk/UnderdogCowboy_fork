# screens/session_screen.py

from textual.screen import Screen
from session_manager import SessionManager
from state_management.storage_interface import StorageInterface
from state_management.json_storage_manager import JSONStorageManager
from events.session_events import SessionSyncStopped, SessionSelected, NewSessionCreated
from textual import on

class SessionScreen(Screen):
    """Base class for session-related screens."""

    def __init__(
        self,
        storage_interface: StorageInterface = None,
        state_machine: 'StateMachine' = None,  # Replace 'StateMachine' with your actual type
        session_manager: SessionManager = None,
        *args,
        **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.state_machine = state_machine
        self.storage_interface = storage_interface or JSONStorageManager()
        self.session_manager = session_manager or SessionManager(self.storage_interface)

    def set_session_manager(self, new_session_manager: SessionManager):
        """Set a new SessionManager and update the UI accordingly."""
        self.session_manager = new_session_manager
        self.update_ui_after_session_load()

    def emit_sync_stopped(self):
        """Emit the SessionSyncStopped message."""
        self.post_message(SessionSyncStopped(screen=self))

    @on(SessionSelected)
    def on_session_selected(self, event: SessionSelected):
        """Handle session selection and notify the main app."""
        try:
            self.session_manager.load_session(event.session_name)
            self.notify(f"Session '{event.session_name}' loaded successfully")
            self.update_header(session_name=event.session_name)
            self.update_ui_after_session_load()
            # Correctly emit the custom message using 'post_message()'
            self.emit_sync_stopped()
        except ValueError as e:
            self.notify(f"Error loading session: {str(e)}", severity="error")

    @on(NewSessionCreated)
    def on_new_session_created(self, event: NewSessionCreated):
        """Handle new session creation and notify the main app."""
        try:
            self.session_manager.create_session(event.session_name)
            self.notify(f"New session '{event.session_name}' created successfully")
            self.update_header(session_name=event.session_name)
            self.update_ui_after_session_load()
            # Correctly emit the custom message using 'post_message()'
            self.emit_sync_stopped()
        except ValueError as e:
            self.notify(f"Error creating session: {str(e)}", severity="error")

    def update_ui_after_session_load(self):
        """Refresh UI elements based on the current session state."""
        raise NotImplementedError("Child classes must implement 'update_ui_after_session_load'")

    def update_header(self, session_name=None, agent_name=None):
        """Update the header with session and agent information."""
        raise NotImplementedError("Child classes must implement 'update_header'")
