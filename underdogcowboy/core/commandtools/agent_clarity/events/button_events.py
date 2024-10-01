from textual.message import Message


class UIButtonPressed(Message):
    def __init__(self, button_id: str):
        self.button_id = button_id
        super().__init__()