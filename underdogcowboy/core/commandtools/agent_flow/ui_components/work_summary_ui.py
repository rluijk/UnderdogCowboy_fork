
# Textual
from textual.app import  ComposeResult
from textual.containers import Vertical
from textual.widgets import  TextArea, Label


# UI
from ui_components.session_dependent import SessionDependentUI

class WorkSummaryUI(SessionDependentUI):
        
    def compose(self) -> ComposeResult:
      
        # Create the UI layout with a text area, submit, and cancel buttons
        with Vertical(id="work-summary-container"):
            yield Label("Summary:")
            yield TextArea(id="summary-message") 

