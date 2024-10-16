import logging

from textual import on
from textual.containers import  Vertical
from textual.widgets import Button,  Label, Static, Input

from events.dialog_events import NewDialogCreated 
from events.button_events import UIButtonPressed


class NewDialogUI(Static):
    """A UI for creating a new dialog."""

    def compose(self):
        yield Vertical(
            Static("Create a new dialog:", id="new-dialog-prompt"),
            Label("Enter a name for the new dialog:", id="dialog-name-label"),
            Input(placeholder="Dialog name", id="dialog-name-input"),
            Button("Create Dialog", id="create-button", disabled=True),
            Button("Cancel", id="cancel-button")
        )

    def on_mount(self):
        self.query_one("#dialog-name-input").focus()

    def on_input_changed(self, event: Input.Changed):
        if event.input.id == "dialog-name-input":
            self.query_one("#create-button").disabled = len(event.value.strip()) == 0

    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "create-button":
            dialog_name = self.query_one("#dialog-name-input").value.strip()
            if dialog_name:
                self.post_message(NewDialogCreated(dialog_name))
        elif event.button.id == "cancel-button":
            self.post_message(UIButtonPressed("cancel-new-dialog"))

    @on(NewDialogCreated)
    def create_new_dialog(self, event: NewDialogCreated):
        # Create Dialog in File System
        pass                