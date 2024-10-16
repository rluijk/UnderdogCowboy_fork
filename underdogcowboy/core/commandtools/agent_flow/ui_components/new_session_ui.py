import logging

from textual.containers import  Vertical
from textual.widgets import Button,  Label, Static, Input

from events.session_events import NewSessionCreated 
from events.button_events import UIButtonPressed


class NewSessionUI(Static):
    """A UI for creating a new session."""

    def compose(self):
        yield Vertical(
            Static("Create a new session:", id="new-session-prompt"),
            Label("Enter a name for the new session:", id="session-name-label"),
            Input(placeholder="Session name", id="session-name-input"),
            Button("Create Session", id="create-button", disabled=True),
            Button("Cancel", id="cancel-button")
        )

    def on_mount(self):
        self.query_one("#session-name-input").focus()

    def on_input_changed(self, event: Input.Changed):
        if event.input.id == "session-name-input":
            self.query_one("#create-button").disabled = len(event.value.strip()) == 0

    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "create-button":
            session_name = self.query_one("#session-name-input").value.strip()
            if session_name:
                self.post_message(NewSessionCreated(session_name))
        elif event.button.id == "cancel-button":
            self.post_message(UIButtonPressed("cancel-new-session"))