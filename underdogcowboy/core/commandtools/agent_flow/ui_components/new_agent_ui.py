import logging
import os
import json


from textual import on
from textual.containers import  Vertical
from textual.widgets import Button,  Label, Static, Input

from events.agent_events import NewAgentCreated 
from events.button_events import UIButtonPressed

# UC

class NewAgentUI(Static):
    """A UI for creating a new agent."""

    def compose(self):
        yield Vertical(
            Static("Create a new agent:", id="new-agent-prompt"),
            Label("Enter a name for the new agent:", id="agent-name-label"),
            Input(placeholder="Agent name", id="agent-name-input"),
            Button("Create Agent", id="create-button", disabled=True),
            Button("Cancel", id="cancel-button")
        )

    def on_mount(self):
        self.query_one("#agent-name-input").focus()

    def on_input_changed(self, event: Input.Changed):
        if event.input.id == "agent-name-input":
            self.query_one("#create-button").disabled = len(event.value.strip()) == 0

    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "create-button":
            dialog_name = self.query_one("#agent-name-input").value.strip()
            if dialog_name:
                self.post_message(NewAgentCreated(dialog_name))
        elif event.button.id == "cancel-button":
            self.post_message(UIButtonPressed("cancel-new-agent"))

