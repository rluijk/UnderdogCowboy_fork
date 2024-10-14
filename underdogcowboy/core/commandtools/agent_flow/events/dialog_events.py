import logging
from textual.message import Message
from rich.text import Text

#uc
from underdogcowboy.core.timeline_editor import CommandProcessor

class DialogSelected(Message):
    def __init__(self, dialog_name: Text):
        self.dialog_name = dialog_name  # Store the actual Text object
        logging.info(f"DialogSelected message created with agent_name: {self.dialog_name}")
        super().__init__()

class NewDialogCreated(Message):
    def __init__(self, dialog_name: str):
        self.dialog_name = dialog_name
        super().__init__()

class LoadDialog(Message):
    def __init__(self, dialog_name: str):
        self.dialog_name = dialog_name
        super().__init__()

class DialogLoaded(Message):
    def __init__(self, processor: CommandProcessor ):
        self.processor = processor
        super().__init__()
