from textual.app import App, ComposeResult
from textual.widget import Widget
from textual.widgets import Input
from textual.containers import Grid
from textual import events

class TinyButton(Widget):
    """A custom button that mimics a smaller button and handles click events."""

    DEFAULT_CSS = """
    TinyButton {
        width: 35;
        height: 3;
        max-width: 35;  /* Maximum width of the button */
        text-align: center;
        border: red;
        padding: 1;
        margin: 0;
        background: whitesmoke;
    }

    TinyButton:hover {
        background: lightgray;
    }
    """

    def __init__(self, label: str) -> None:
        super().__init__()
        self.label = label

    def render(self) -> str:
        """Render the button's label (in this case, the refresh symbol)."""
        return self.label

    async def on_click(self, event: events.Click) -> None:
        """Handle the click event on the button."""
        # Add your custom logic here. For now, we just log a message.
        self.app.set_status(f"Button '{self.label}' clicked!")

class InputButtonWidget(Widget): #test to delete
    """A composite widget with an input box and a custom small button."""

    DEFAULT_CSS = """
    InputButtonWidget {
        width: auto;
        height: auto;
    }

    InputButtonWidget Grid {
        max-width: 55;
        grid-size: 2;
        grid-columns: 1fr auto;  /* Make the button smaller compared to the input */
    }

    InputButtonWidget Input {
        width: 1fr;
        height: auto;
        border: grey;
        background: whitesmoke;
    }
    """

    def compose(self) -> ComposeResult:
        """Compose an input box and a small button."""
        with Grid():
            yield Input(placeholder="Enter text here", id="input-box")
            yield TinyButton("R")  # Using the custom TinyButton

class InputButtonApp(App):
    """App demonstrating an input box and a custom tiny refresh button."""

    CSS = """
    Screen {
        align: center middle;
    }
    """

    def compose(self) -> ComposeResult:
        """Compose the application layout with the composite widget."""
        yield InputButtonWidget()

if __name__ == "__main__":
    InputButtonApp().run()
