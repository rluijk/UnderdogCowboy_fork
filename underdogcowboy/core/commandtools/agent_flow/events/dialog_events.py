import logging
from textual.message import Message
from rich.text import Text

class DialogSelected(Message):
    def __init__(self, dialog_name: Text):
        self.dialog_name = dialog_name  # Store the actual Text object
        logging.info(f"DialogSelected message created with agent_name: {self.dialog_name}")
        super().__init__()
