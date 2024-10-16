"""
MultiScreenApp: An Asynchronous Multi-Screen Textual User Interface with LLM Call Simulation

This Python script is an example of a multi-screen interactive application using the Textual framework.
It demonstrates how to handle asynchronous tasks in a responsive UI with multiple screens and concurrent operations.

Key Components:
1. **SessionManager**: This class manages the state of input data across different screens, ensuring data persistence between interactions.
2. **LLMCallManager**: Manages asynchronous calls to a mock LLM (Large Language Model). It uses a thread pool to simulate concurrent processing, ensuring that the UI remains responsive.
3. **InputBoxScreen**: The main screen where users can input data and trigger LLM calls using buttons. Each button simulates an LLM response for the associated input box.
4. **OtherScreen**: A secondary screen for navigation testing, showcasing the multi-screen functionality.
5. **MultiScreenApp**: The main application class managing the screens and orchestrating the flow between them.

Key Features:
- **ThreadPoolExecutor for Concurrency**: Both the `LLMCallManager` and `InputBoxScreen` use thread pools to handle concurrent tasks without blocking the main UI thread.
- **Asynchronous Operations**: LLM calls are simulated asynchronously to keep the interface reactive and prevent it from freezing during background processing.
- **State Management**: The `SessionManager` handles saving and retrieving data, enabling users to navigate between screens without losing information.
- **Logging**: Detailed logging is added for debugging and monitoring purposes, with log messages written to a file (`app.log`) to provide insights into the application's runtime behavior.

This example is ideal for developers looking to build interactive UIs with asynchronous backend tasks, providing a clear structure to manage state, handle user interactions, and perform non-blocking operations efficiently.
"""

from concurrent.futures import ThreadPoolExecutor
import asyncio
import logging
from textual.app import App, ComposeResult
from textual.widgets import Button, Input, Label
from textual.containers import Horizontal
from textual.screen import Screen

# Configure logging to output to a file only
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s', handlers=[
    logging.FileHandler("app.log")
])

class SessionManager:
    """Manages session data for storing and retrieving information between screens."""
    def __init__(self):
        self.data = {}  # Dictionary to store key-value pairs for session data

    def update_data(self, key, value):
        """Update or add data to the session."""
        logging.debug(f"Updating session data: {key} = {value}")
        self.data[key] = value

    def get_data(self, key):
        """Retrieve data from the session by key."""
        value = self.data.get(key, None)
        logging.debug(f"Retrieving session data: {key} = {value}")
        return value


class LLMCallManager:
    """Manages LLM calls asynchronously."""
    def __init__(self, max_workers=5):
        # The `self.executor` here is used to manage LLM calls asynchronously, allowing for concurrent processing of multiple LLM requests.
        # This enables the UI to remain responsive even when multiple LLM calls are happening.
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        logging.debug("Initialized LLMCallManager with ThreadPoolExecutor")

    async def run_llm_call(self, llm_function, *args):
        """Run a generic LLM function asynchronously using a thread pool executor."""
        # By running the LLM function in an executor, we prevent blocking the event loop, thus keeping the UI responsive.
        logging.debug(f"Running LLM function {llm_function.__name__} with arguments: {args}")
        return await asyncio.get_event_loop().run_in_executor(self.executor, llm_function, *args)


class InputBoxScreen(Screen):
    """Concrete screen handling input boxes and buttons that trigger LLM calls."""
    def __init__(self, session_manager):
        super().__init__()
        self.session_manager = session_manager
        # The `self.executor` here is used to handle multiple UI-related tasks concurrently, such as LLM calls triggered by different buttons.
        # This ensures that user interactions like button presses do not block other tasks or freeze the UI.
        self.executor = ThreadPoolExecutor(max_workers=5)  # Allow multiple LLM calls
        self.llm_call_manager = LLMCallManager()
        self.input_boxes = []  # Store the input box widgets to manage their state
        logging.debug("InputBoxScreen initialized with LLMCallManager and ThreadPoolExecutor")

    def compose(self) -> ComposeResult:
        """Compose the UI elements for the screen."""
        yield Label("Input Box Screen")  # Label to indicate the purpose of the screen
        for i in range(1, 6):  # Create 5 input boxes with corresponding buttons
            input_id = f"input-{i}"
            input_box = Input(placeholder=f"Input {i}", id=input_id)
            button = Button(f"Fetch {i}", id=f"button-{i}")
            self.input_boxes.append(input_box)  # Track input boxes for later state management
            yield Horizontal(input_box, button)  # Arrange input box and button horizontally
        yield Button("Go to Other Screen", id="switch-screen")  # Button to navigate to another screen
        logging.debug("InputBoxScreen UI composed with input boxes and buttons")

    def on_mount(self):
        """Handle what happens when the screen is displayed or re-displayed."""
        # Restore the state of the input boxes from the session manager.
        for input_box in self.input_boxes:
            stored_value = self.session_manager.get_data(input_box.id)
            if stored_value:
                input_box.value = stored_value  # Set the input box value if previously stored
            input_box.disabled = False  # Ensure input boxes are editable when screen is re-displayed
        logging.debug("InputBoxScreen mounted and input boxes restored from session data")

        # Reset buttons to their default state
        for button in self.query("Button"):
            button.disabled = False  # Make sure buttons are not disabled
            label_text = str(button.label)  # Convert the label to string for checking
            if label_text.startswith("Loading"):
                button.label = f"Fetch {button.id[-1]}"  # Reset to original label if it was in 'Loading' state
        logging.debug("InputBoxScreen buttons reset to default state")

    async def on_button_pressed(self, event: Button.Pressed):
        """Handle button press events."""
        button_id = event.button.id
        logging.info(f"Button pressed: {button_id}")
        if button_id.startswith("button-"):
            # Identify the corresponding input box for the button pressed
            input_id = button_id.replace("button-", "input-")
            input_box = self.query_one(f"#{input_id}", Input)
            button = event.button

            # Update button state to show it's processing (await ensures immediate visual feedback)
            await self.set_button_loading(button)

            # Run LLM simulation using the LLM call manager for background processing
            # Using `asyncio.create_task` allows the LLM call to run in the background without blocking the UI
            asyncio.create_task(self.run_llm_simulation(input_box, button))

        elif button_id == "switch-screen":
            # Switch to the other screen when the switch button is pressed
            await self.app.push_screen("OtherScreen")

    async def set_button_loading(self, button: Button):
        """Sets the button to 'Loading...' state to indicate processing."""
        logging.debug(f"Setting button {button.id} to loading state")
        button.label = "Loading..."
        button.disabled = True  # Disable the button to prevent multiple clicks while processing
        await asyncio.sleep(0)  # Yield control to event loop to reflect UI changes immediately

    async def run_llm_simulation(self, input_box: Input, button: Button) -> None:
        """Simulate an LLM call using the LLM manager to keep the UI responsive."""
        try:
            # Simulate calling the LLM and retrieving a response
            logging.debug(f"Starting LLM simulation for input box {input_box.id}")
            result = await self.llm_call_manager.run_llm_call(self.simulate_llm_call, input_box)

            # Once the LLM call is complete, update the UI with the result
            self.update_and_show_result(input_box, result)
            logging.info(f"LLM simulation completed for input box {input_box.id} with result: {result}")

        except Exception as e:
            # Print any errors that occur during the LLM simulation
            logging.error(f"Error during LLM simulation: {e}")

        finally:
            # Reset the button state after processing is complete
            button.label = f"Fetch {input_box.id[-1]}"
            button.disabled = False
            logging.debug(f"Button {button.id} reset to default state")

    def simulate_llm_call(self, input_box: Input) -> str:
        """Simulate the LLM call with a delay to mimic network latency."""
        import time
        logging.debug(f"Simulating LLM call for input box {input_box.id}")
        time.sleep(5)  # Simulate network delay with a sleep
        return f"LLM Response for {input_box.id}"  # Return a mock response for the input box

    def update_and_show_result(self, input_box: Input, result: str) -> None:
        """Update the input box with the LLM result and store it in the session."""
        input_box.value = result  # Set the input box value to the LLM result
        self.session_manager.update_data(input_box.id, result)  # Store the result in the session manager
        logging.debug(f"Updated input box {input_box.id} with result: {result}")


class OtherScreen(Screen):
    """A placeholder screen for navigation testing."""
    def __init__(self, session_manager):
        super().__init__()
        self.session_manager = session_manager
        logging.debug("OtherScreen initialized")

    def compose(self) -> ComposeResult:
        """Compose the UI elements for the other screen."""
        yield Label("This is another screen.")  # Label indicating this is a different screen
        yield Button("Go Back to Input Screen", id="back-button")  # Button to navigate back to the input screen
        logging.debug("OtherScreen UI composed with label and back button")

    async def on_button_pressed(self, event: Button.Pressed):
        """Handle button press events for navigation."""
        if event.button.id == "back-button":
            logging.info("Back button pressed, navigating to InputBoxScreen")
            # Navigate back to the InputBoxScreen when the button is pressed
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
        self.session_manager = SessionManager()  # Initialize the session manager to store data between screens
        logging.debug("MultiScreenApp initialized with SessionManager")

    def on_mount(self) -> None:
        """Mount screens when the app starts."""
        # The use of `install_screen` here is crucial to ensure the UI remains responsive and doesn't freeze.
        # It allows for smooth screen switching and proper management of resources, especially with concurrent LLM calls.
        self.install_screen(lambda: InputBoxScreen(self.session_manager), name="InputBoxScreen")
        # Installing the `OtherScreen` using `install_screen` is important for maintaining UI fluidity when navigating between different screens.
        # This helps in ensuring that the transition does not block or freeze the application.
        self.install_screen(lambda: OtherScreen(self.session_manager), name="OtherScreen")
        logging.debug("Screens installed: InputBoxScreen and OtherScreen")

        # Start with the Input Box screen
        self.push_screen("InputBoxScreen")
        logging.info("Application started with InputBoxScreen")


if __name__ == "__main__":
    logging.info("Starting MultiScreenApp")
    app = MultiScreenApp()
    app.run()
    logging.info("MultiScreenApp has terminated")