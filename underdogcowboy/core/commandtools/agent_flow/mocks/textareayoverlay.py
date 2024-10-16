import logging
from textual.app import App, ComposeResult
from textual.widgets import TextArea, Input
from textual.containers import Container
from textual.message import Message

# Setup logging to a file
logging.basicConfig(filename='text_selection_app.log', level=logging.DEBUG, format='%(asctime)s - %(message)s')

class SelectionInputOverlay(Container):
    """A small overlay for user input over the selection."""

    def __init__(self, initial_value: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.initial_value = initial_value
    
    def compose(self) -> ComposeResult:
        """Mount the Input widget after the parent is mounted."""
        yield Input(value=self.initial_value)
    
    def get_input_value(self) -> str:
        """Return the value of the Input widget."""
        input_widget = self.query(Input).first()
        return input_widget.value if input_widget else ""

class TextSelectionApp(App):
    def __init__(self):
        super().__init__()
        self.text_area = TextArea(text="Start your journey with our AI agency!\nSelect this text.", soft_wrap=True)
        self.input_overlay = None
        self.selection_start = None
        self.selection_end = None

    def compose(self) -> ComposeResult:
        yield self.text_area

    async def on_text_area_selection_changed(self, message: Message) -> None:
        """Triggered when selection changes in TextArea."""
        selection = self.text_area.selected_text
        if selection and not self.input_overlay:
            # Store the selection start and end locations
            self.selection_start, self.selection_end = self.text_area.selection.start, self.text_area.selection.end
            
            # Log the selection details
            logging.debug(f"Selection changed: start={self.selection_start}, end={self.selection_end}, text='{selection}'")
            
            # Create the input overlay
            self.input_overlay = SelectionInputOverlay(selection)
            
            # Mount the input overlay
            await self.mount(self.input_overlay)
            self.input_overlay.styles.absolute_position = "10 10"  # Adjust position dynamically

    async def on_input_submitted(self, message: Message) -> None:
        """Handle the input submission."""
        if self.input_overlay and self.selection_start is not None:
            new_value = self.input_overlay.get_input_value()

            # Log before replacing text
            logging.debug(f"Input submitted: new_value='{new_value}', selection_start={self.selection_start}, selection_end={self.selection_end}")

            # Clear the selected text before replacing
            self.text_area.replace("", self.selection_start, self.selection_end)

            # Log after clearing the text
            logging.debug(f"Text after clearing selection: '{self.text_area.text}'")

            # Insert the new value at the start of the selection
            self.text_area.insert(new_value, self.selection_start)

            # Log after inserting the new value
            logging.debug(f"Text after inserting new value: '{self.text_area.text}'")

            # Clean up the input overlay and reset the selection range
            await self.input_overlay.remove()
            self.input_overlay = None
            self.selection_start = self.selection_end = None

if __name__ == "__main__":
    app = TextSelectionApp()
    app.run()