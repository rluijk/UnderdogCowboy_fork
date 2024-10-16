import logging
from textual.message import Message
from textual.events import Event


class SessionSelected(Message):
    def __init__(self, session_name: str):
        self.session_name = session_name
        logging.info(f"SessionSelected message created with session_name: {session_name}")
        super().__init__()

class NewSessionCreated(Message):
    def __init__(self, session_name: str):
        self.session_name = session_name
        super().__init__()

class SessionSyncStopped(Event):
    """Event indicating that session synchronization should stop."""
    def __init__(self, screen: 'SessionScreen'):
        super().__init__()
        self.screen = screen

class SessionStateChanged(Message):
    def __init__(self, source, session_active: bool, session_name: str = None):
        super().__init__()
        self.source = source
        self.session_active = session_active  # Indicates if a session is active
        self.session_name = session_name      # Optional name of the loaded session
