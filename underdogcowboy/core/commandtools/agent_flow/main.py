from concurrent.futures import ThreadPoolExecutor
import asyncio
from textual.app import App, ComposeResult
from textual.widgets import Input, Button, Label
from textual.containers import Horizontal
from textual.screen import Screen


class SessionManager:
    def __init__(self):
        self.data = {}

    def update_data(self, key, value):
        self.data[key] = value

    def get_data(self, key):
        return self.data.get(key, None)


class InputBoxScreen(Screen):
    def __init__(self, session_manager):
        super().__init__()
        self.session_manager = session_manager
        self.executor = ThreadPoolExecutor(max_workers=5)  # Allow multiple LLM calls
        self.input_boxes = []  # Store the input box widgets to manage their state

    def compose(self) -> ComposeResult:
        yield Label("Input Box Screen")
        for i in range(1, 6):  # Create 5 input boxes with buttons
            input_id = f"input-{i}"
            input_box = Input(placeholder=f"Input {i}", id=input_id)
            button = Button(f"Fetch {i}", id=f"button-{i}")
            self.input_boxes.append(input_box)
            yield Horizontal(input_box, button)
        yield Button("Go to Other Screen", id="switch-screen")

    def on_mount(self):
        """Handle what happens when the screen is displayed or re-displayed."""
        # Reset the input boxes and buttons to their initial states
        for input_box in self.input_boxes:
            stored_value = self.session_manager.get_data(input_box.id)
            if stored_value:
                input_box.value = stored_value
            input_box.disabled = False  # Ensure input boxes are editable

        # Reset buttons
        for button in self.query("Button"):
            button.disabled = False  # Make sure buttons are not disabled
            label_text = str(button.label)  # Convert the label to string for checking
            if label_text.startswith("Loading"):
                button.label = f"Fetch {button.id[-1]}"  # Reset to original label

    async def on_button_pressed(self, event: Button.Pressed):
        button_id = event.button.id
        if button_id.startswith("button-"):
            input_id = button_id.replace("button-", "input-")
            input_box = self.query_one(f"#{input_id}", Input)
            button = event.button

            # Update button state to show it's processing (await ensures immediate visual feedback)
            await self.set_button_loading(button)

            # Run LLM simulation
            asyncio.create_task(self.run_llm_simulation(input_box, button))

        elif button_id == "switch-screen":
            await self.app.push_screen("OtherScreen")

    async def set_button_loading(self, button: Button):
        """Sets the button to 'Loading...' state."""
        button.label = "Loading..."
        button.disabled = True
        await asyncio.sleep(0)  # Yield control to event loop to reflect UI changes

    async def run_llm_simulation(self, input_box: Input, button: Button) -> None:
        """Method to simulate an LLM call using the working approach from perform_analysis"""
        try:
            # Simulating LLM configuration and agent name
            llm_config = "Mock LLM Config"
            current_agent = "Mock Agent"

            # Simulate the LLM processing in a background thread
            with ThreadPoolExecutor(max_workers=1) as executor:
                result = await asyncio.get_event_loop().run_in_executor(
                    executor, self.simulate_llm_call, input_box
                )

            if result.startswith("Error:"):
                raise ValueError(result)

            # Once complete, update the UI with the result
            self.update_and_show_result(input_box, result)

        except Exception as e:
            print(f"Error during LLM simulation: {e}")

        finally:
            # Reset button state after processing
            button.label = f"Fetch {input_box.id[-1]}"
            button.disabled = False

    def simulate_llm_call(self, input_box: Input) -> str:
        """Simulate the LLM call with a delay, as in the working example."""
        import time
        time.sleep(2)  # Simulate network delay
        result = f"LLM Response for {input_box.id}"
        self.session_manager.update_data(input_box.id, result)
        return result

    def update_and_show_result(self, input_box: Input, result: str) -> None:
        """Update the input box with the result."""
        input_box.value = result


class OtherScreen(Screen):
    def __init__(self, session_manager):
        super().__init__()
        self.session_manager = session_manager

    def compose(self) -> ComposeResult:
        yield Label("This is another screen.")
        yield Button("Go Back to Input Screen", id="back-button")

    async def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "back-button":
            await self.app.push_screen("InputBoxScreen")


class MultiScreenApp(App):
    """Main application managing multiple screens."""

    CSS = """
    Horizontal { margin-bottom: 1; }
    Input {
        width: 60%;
        margin-right: 2;
    }
    Button {
        background: #5A9BD5;
        color: white;
        padding: 1;
        border: none;
        width: 20%;
        text-align: center;
    }
    Button:disabled {
        background: gray;
        color: lightgray;
    }
    """

    def __init__(self):
        super().__init__()
        self.session_manager = SessionManager()

    def on_mount(self) -> None:
        """Mount screens when the app starts."""
        # Install screens using install_screen
        self.install_screen(lambda: InputBoxScreen(self.session_manager), name="InputBoxScreen")
        self.install_screen(lambda: OtherScreen(self.session_manager), name="OtherScreen")

        # Start with the Input Box screen
        self.push_screen("InputBoxScreen")


if __name__ == "__main__":
    app = MultiScreenApp()
    app.run()
