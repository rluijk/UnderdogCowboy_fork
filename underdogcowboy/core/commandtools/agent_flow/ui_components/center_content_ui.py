
from textual.app import ComposeResult
from textual.events import Mount
from textual.widgets import Label, Static

class CenterContent(Static):
    def __init__(self, action: str = None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.action = action

    def compose(self) -> ComposeResult:
        yield Label(f"")
        #yield Label(f"Content for action: {self.action}")

    #def _on_mount(self, event: Mount) -> None:
        #pass
        #self.app.notify(f"{self.action}", severity="information")