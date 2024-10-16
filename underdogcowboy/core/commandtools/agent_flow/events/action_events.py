from textual.message import Message

class ActionSelected(Message):
    def __init__(self, action: str):
        self.action = action
        super().__init__()

"""

from textual.events import Event

class ActionSelected(Event):
    def __init__(self, action: str, *, sender):
        self.action = action
        super().__init__(sender=sender, bubble=True)
"""