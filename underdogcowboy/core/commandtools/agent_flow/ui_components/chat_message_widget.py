
import logging
from textual.widget import Widget
from textual.app import ComposeResult
from textual.widgets import Static, Button
from textual.containers import Vertical, Horizontal
from rich.markdown import Markdown

class ChatMessageWidget(Widget):
    def __init__(self, message_id, role, text, **kwargs):
        super().__init__(**kwargs)
        self.message_id = message_id  # Unique identifier for the message
        self.role = role  # "User" or "Assistant"
        self.text = text  # Message text

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Static(Markdown(f"#### {self.role}:\n{self.text}"), classes="message-text")
            with Horizontal(classes="message-buttons"):
                yield Button("Copy", id=f"copy-{self.message_id}", classes="message-button")
                yield Button("Export", id=f"export-{self.message_id}", classes="message-button")
                # Add more buttons as needed

    def on_button_pressed(self, event: Button.Pressed):
        button_id = event.button.id
        if button_id == f"copy-{self.message_id}":
            self.copy_message()
        elif button_id == f"export-{self.message_id}":
            self.export_message()

    def copy_message(self):
        # Implement the logic to copy self.text to the clipboard
        logging.info(f"Copying message {self.message_id} to clipboard.")
        self.app.clipboard_content.copy(self.text)
        self.app.notify(f"Copied message to clipboard.")

    def export_message(self):
        # Implement the logic to export self.text to a markdown file
        filename = f"message_{self.message_id}.md"
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(self.text)
        logging.info(f"Exported message {self.message_id} to {filename}.")
        self.app.notify(f"Exported message to {filename}.")

    def update_message(self, new_text):
        self.text = new_text
        # Update the displayed text
        message_static = self.query_one(".message-text", Static)
        message_static.update(Markdown(f"#### {self.role}:\n{self.text}"))
