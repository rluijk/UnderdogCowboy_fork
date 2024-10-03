from textual.app import App, ComposeResult
from textual.widgets import Static, Button, LoadingIndicator
from textual.containers import Vertical
from textual.message import Message
import asyncio

class TestApp(App):

    class TaskComplete(Message):
        def __init__(self, result: str):
            self.result = result
            super().__init__()

    class TaskError(Message):
        def __init__(self, error: str):
            self.error = error
            super().__init__()

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Static("Initial Dummy Text", id="text-display")
            yield Button("Re-run", id="rerun-button")
            yield LoadingIndicator(id="loading")

    def on_mount(self) -> None:
        self.query_one("#loading").display = False

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "rerun-button":
            self.run_task()

    def run_task(self) -> None:
        # Show the loading indicator
        self.query_one("#loading").display = True
        self.query_one("#text-display").update("Waiting for response...")

        # Create a task to run the long-running operation
        asyncio.create_task(self.perform_long_task())

    async def perform_long_task(self) -> None:
        try:
            await asyncio.sleep(5)  # Simulate a long-running task
            self.post_message(self.TaskComplete("New Text After 5 Seconds"))
        except Exception as e:
            self.post_message(self.TaskError(str(e)))

    def on_test_app_task_complete(self, message: "TestApp.TaskComplete") -> None:
        self.query_one("#loading").display = False
        self.query_one("#text-display").update(message.result)

    def on_test_app_task_error(self, message: "TestApp.TaskError") -> None:
        self.query_one("#loading").display = False
        self.query_one("#text-display").update(f"Error: {message.error}")

if __name__ == "__main__":
    app = TestApp()
    app.run()