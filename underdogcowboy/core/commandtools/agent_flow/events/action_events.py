from textual.message import Message

class ActionSelected(Message):
    def __init__(self, action: str):
        self.action = action
        super().__init__()
