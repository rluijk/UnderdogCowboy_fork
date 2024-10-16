import logging

# Textual
from textual.app import  ComposeResult
from textual.containers import Vertical
from textual.widgets import  (  Button, Static, Label, TextArea )

# Clarity System 
# UI
from ui_components.dynamic_container import  DynamicContainer
from ui_components.session_dependent import SessionDependentUI

# Events
from events.button_events import UIButtonPressed

class SystemMessageUI(SessionDependentUI):
    """A UI for creating and submitting a system message."""
        
    def compose(self) -> ComposeResult:
        # Retrieve any existing system message from the storage manager
        stored_message = self.session_manager.get_data("system_message")
        if stored_message is None:
            stored_message = ""  # Set to empty if no message is found
        
        # Create the UI layout with a text area, submit, and cancel buttons
        with Vertical(id="system-message-container"):
            yield Label("Enter your system message:")
            yield TextArea(id="system-message-input", text=stored_message)  # Pre-populate if there's a stored message
            yield Button("Submit", id="submit-system-message", classes="action-button")
            yield Button("Cancel", id="cancel-system-message", classes="action-button")

    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "submit-system-message":
            # Retrieve the message from the text area
            system_message = self.query_one("#system-message-input").text
            # Log and store the system message
            logging.info(f"System message submitted: {system_message}")
            self.session_manager.update_data("system_message", system_message)
            
            # Clear the UI after submission by posting a message
            self.app.query_one(DynamicContainer).clear_content()
            self.app.notify("System message stored successfully.")
        
        elif event.button.id == "cancel-system-message":
            # Post a message instead of clearing the UI directly, ensuring consistency
            self.post_message(UIButtonPressed("cancel-system-message"))
