from textual.app import App, ComposeResult
from textual.widgets import Static, Button, LoadingIndicator
from textual.containers import Vertical
import asyncio

class TestApp(App):

    def compose(self) -> ComposeResult:
        with Vertical():
            # Initial dummy text
            self.text_display = Static("Initial Dummy Text", id="text-display")
            yield self.text_display
            # Re-run button to trigger the task
            yield Button("Re-run", id="rerun-button")
            # Loading indicator, but NOT shown initially (not part of the layout yet)
            self.loading = LoadingIndicator(id="loading")
    
    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "rerun-button":
            # When button is pressed, mount (show) the loading indicator in the UI
            self.mount(self.loading)
            self.text_display.update("Waiting for response...")

            await self.simulate_long_task()  # Simulate a long-running task

            # After task completion, remove the indicator and update the text
            self.loading.remove()
            self.text_display.update("New Text After 5 Seconds")

    async def simulate_long_task(self):
        await asyncio.sleep(5)  # Simulate a delay

if __name__ == "__main__":
    app = TestApp()
    app.run()
