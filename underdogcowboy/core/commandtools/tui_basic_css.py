
from textual.app import App, ComposeResult
from textual.widgets import  Button

class BasicApp(App):
    """A basic app demonstrating CSS"""

 
    CSS_PATH = "basic_css.css" 

    def on_load(self):
        """Bind keys here."""
        self.bind("tab", "toggle_class('#sidebar', '-active')")

    def compose(self) -> ComposeResult:
        yield Button( id=f"btn-1" , classes="action-button")
     



# Correct way to run the app
if __name__ == "__main__":
    app = BasicApp()
    app.run()