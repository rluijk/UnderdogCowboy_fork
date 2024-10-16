
from textual.app import ComposeResult
from textual.widgets import Label, Static

class CenterContent(Static):
    def __init__(self, action: str = None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.action = action

    def compose(self) -> ComposeResult:
        yield Label(f"Content for action: {self.action}")
