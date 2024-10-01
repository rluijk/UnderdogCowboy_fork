import logging
from textual.message import Message

class SessionSelected(Message):
    def __init__(self, session_name: str):
        self.session_name = session_name
        logging.info(f"SessionSelected message created with session_name: {session_name}")
        super().__init__()

class NewSessionCreated(Message):
    def __init__(self, session_name: str):
        self.session_name = session_name
        super().__init__()