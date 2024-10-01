from textual.app import ComposeResult
from textual.widgets import Button
from textual.containers import Container, Grid

""" System Clarity """
# Events
from events.button_events import UIButtonPressed

class LeftSideButtons(Container):
    
    border_title = "Options"  # Set the border title here as a class attribute
    def compose(self) -> ComposeResult:
        with Grid(id="left-side-buttons", classes="left-side-buttons"):
            yield Button("New", id="new-button", classes="left-side-button")
            yield Button("Load", id="load-session", classes="left-side-button")
            
    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.post_message(UIButtonPressed(event.button.id))

class LeftSideContainer(Container):
    def compose(self) -> ComposeResult:
        yield LeftSideButtons()
