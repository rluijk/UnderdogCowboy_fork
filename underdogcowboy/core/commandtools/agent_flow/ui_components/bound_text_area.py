
import logging

# textual
from textual.binding import Binding
from textual.widgets import TextArea

# events
from events.chat_events import TextSubmitted


class BoundTextArea(TextArea):
    BINDINGS = [
        Binding("ctrl+s", "submit", "Submit", key_display="Ctrl+s", priority=True),
    ]

    def action_submit(self) -> None:
        """Handle the submit action."""
        message = self.text
        logging.info(f"Submitting message from BoundTextArea: {message}")
        self.text = ""
        self.post_message(TextSubmitted(message))

    def disable(self) -> None:
        self.disabled = True
        self.add_class("-disabled")

    def enable(self) -> None:
        self.disabled = False
        self.remove_class("-disabled")