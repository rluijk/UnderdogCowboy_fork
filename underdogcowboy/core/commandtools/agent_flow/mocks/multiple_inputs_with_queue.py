"""
Developer Note:
================
This code implements a multi-screen Textual User Interface (TUI) with a detailed solution for managing asynchronous tasks using a queue and thread pool executor. 
Below is an explanation of the approach taken, why it works effectively for a TUI application, and how you can abstract this design for your own solutions.

### Core Design Elements

1. **LLMCallManager**: This class handles background tasks that simulate calling a Language Learning Model (LLM). It uses a `ThreadPoolExecutor` for managing 
workers to handle concurrent operations and an `asyncio.Queue` for decoupling user-triggered tasks from actual execution.

2. **Concurrency Control**:
    - The `max_workers` parameter controls the number of threads that can run concurrently (`ThreadPoolExecutor`). This is used to cap the number of simultaneous 
    background LLM calls, ensuring system resources are not overwhelmed.
    - The `asyncio.Queue` allows tasks to be queued when there are more button presses than available workers. This keeps the UI responsive by placing tasks into a 
    holding pattern instead of blocking execution or rejecting tasks.

3. **Queue Processing**:
    - A task queue (`task_queue`) is established to hold incoming tasks. The queue is processed continuously by the `process_queue` coroutine, which ensures tasks
      are started as soon as a worker becomes available.
    - The `handle_task` function creates an independent coroutine for each task (`asyncio.create_task`). This ensures that each LLM task runs concurrently within 
    the bounds of the thread pool, without blocking the main event loop.

### Key Advantages

- **Decoupling Input from Processing**: The use of an `asyncio.Queue` allows user interactions (e.g., button presses) to be decoupled from the processing of tasks. 
When a button is pressed, the corresponding LLM call request is placed in the queue instantly. This prevents the UI from freezing, even when all workers are busy.

- **Controlled Concurrency**: By limiting the number of active threads (`max_workers`) while allowing an unbounded queue size, the application can handle surges 
in user input gracefully. The threads take tasks from the queue as they become available, balancing system load and UI responsiveness.

- **Continuous Task Processing**: The `process_queue` method runs continuously as a coroutine (`asyncio.create_task(self.process_queue())`). This ensures the queue
 is always monitored, and new tasks are processed as soon as resources are available.

### How to Abstract for Your Own Solutions

1. **Task Manager Abstraction**: The `LLMCallManager` can be abstracted into a generic task manager that can handle any type of background work, not just LLM calls. 
You could provide it with different worker functions as needed.

2. **Decoupled Worker Management**: Use a similar queue and worker setup to decouple task initiation from execution in any application where user requests might 
exceed the number of concurrent processing units. The queue provides a buffer, ensuring no task is lost, and helps manage spikes in activity.

3. **Continuous Queue Processing**: The `process_queue` loop can be a reusable pattern for applications that need to manage and execute a continuous flow of asynchronous 
tasks. By using a coroutine to monitor the queue and spin off tasks as they become available, you can maintain a fluid user experience.

4. **UI Feedback Management**: The button handling logic (`set_button_loading` and subsequent update) shows how to provide feedback to users on the status of their
 requests. This is crucial in maintaining a good user experience when processing tasks asynchronously. Abstract this part into a UI feedback manager for handling
   states such as "Loading", "Completed", and "Queued".

### Practical Example for Reuse
If you want to use this pattern in your own solution:
- **Replace the LLM Function**: Swap out `simulate_llm_call` for any long-running function you need (e.g., API requests, data processing).
- **Extend Session Management**: Modify `SessionManager` to store additional context or state that needs to persist across screens or sessions.
- **Adjust Thread Pool Size**: Depending on the nature of the tasks (CPU-bound or I/O-bound), adjust `max_workers` accordingly. For I/O-bound tasks (like web requests),
 higher values are more feasible compared to CPU-bound operations.

### Limitations
- **Thread Pool for I/O-Bound Work**: This solution uses `ThreadPoolExecutor`, which is suitable for I/O-bound tasks. If you are dealing with CPU-bound tasks, consider using 
`ProcessPoolExecutor` to avoid being constrained by Python's Global Interpreter Lock (GIL).
- **Queue Backpressure**: Although the queue can hold many tasks, ensure you handle backpressure appropriately if task production greatly outpaces processing. 
You may want to implement a maximum queue size or other throttling mechanisms.

This intricate setup allows you to efficiently handle multiple tasks asynchronously while keeping the UI responsive, which is critical for maintaining a good user experience 
in interactive applications.
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
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.task_queue = asyncio.Queue()  # Queue to hold tasks
        logging.debug("Initialized LLMCallManager with ThreadPoolExecutor and task queue")
        asyncio.create_task(self.process_queue())  # Start the queue processing loop

    async def run_llm_call(self, llm_function, *args):
        """Run a generic LLM function asynchronously using a thread pool executor."""
        logging.debug(f"Running LLM function {llm_function.__name__} with arguments: {args}")
        return await asyncio.get_event_loop().run_in_executor(self.executor, llm_function, *args)

    async def process_queue(self):
        while True:
            llm_function, input_box, button = await self.task_queue.get()
            asyncio.create_task(self.handle_task(llm_function, input_box, button))
            self.task_queue.task_done()

    async def handle_task(self, llm_function, input_box, button):
        result = await self.run_llm_call(llm_function, input_box)
        input_box.value = result
        button.label = f"Fetch {input_box.id[-1]}"
        button.disabled = False
        logging.info(f"LLM simulation completed for input box {input_box.id} with result: {result}")


class InputBoxScreen(Screen):
    """Concrete screen handling input boxes and buttons that trigger LLM calls."""
    def __init__(self, session_manager):
        super().__init__()
        self.session_manager = session_manager
        self.llm_call_manager = LLMCallManager()
        self.input_boxes = []  # Store the input box widgets to manage their state
        logging.debug("InputBoxScreen initialized with LLMCallManager")

    def compose(self) -> ComposeResult:
        """Compose the UI elements for the screen."""
        yield Label("Input Box Screen")
        for i in range(1, 6):
            input_id = f"input-{i}"
            input_box = Input(placeholder=f"Input {i}", id=input_id)
            button = Button(f"Fetch {i}", id=f"button-{i}")
            self.input_boxes.append(input_box)
            yield Horizontal(input_box, button)
        yield Button("Go to Other Screen", id="switch-screen")
        logging.debug("InputBoxScreen UI composed with input boxes and buttons")

    def on_mount(self):
        """Handle what happens when the screen is displayed or re-displayed."""
        for input_box in self.input_boxes:
            stored_value = self.session_manager.get_data(input_box.id)
            if stored_value:
                input_box.value = stored_value
            input_box.disabled = False
        logging.debug("InputBoxScreen mounted and input boxes restored from session data")

        for button in self.query("Button"):
            button.disabled = False
            label_text = str(button.label)
            if label_text.startswith("Loading"):
                button.label = f"Fetch {button.id[-1]}"
        logging.debug("InputBoxScreen buttons reset to default state")

    async def on_button_pressed(self, event: Button.Pressed):
        """Handle button press events."""
        button_id = event.button.id
        logging.info(f"Button pressed: {button_id}")
        if button_id.startswith("button-"):
            input_id = button_id.replace("button-", "input-")
            input_box = self.query_one(f"#{input_id}", Input)
            button = event.button

            await self.set_button_loading(button)
            await self.llm_call_manager.task_queue.put((self.simulate_llm_call, input_box, button))

        elif button_id == "switch-screen":
            await self.app.push_screen("OtherScreen")

    async def set_button_loading(self, button: Button):
        """Sets the button to 'Loading...' state to indicate processing."""
        logging.debug(f"Setting button {button.id} to loading state")
        button.label = "Loading..."
        button.disabled = True
        await asyncio.sleep(0)

    def simulate_llm_call(self, input_box: Input) -> str:
        """Simulate the LLM call with a delay to mimic network latency."""
        import time
        logging.debug(f"Simulating LLM call for input box {input_box.id}")
        time.sleep(5)
        return f"LLM Response for {input_box.id}"


class OtherScreen(Screen):
    """A placeholder screen for navigation testing."""
    def __init__(self, session_manager):
        super().__init__()
        self.session_manager = session_manager
        logging.debug("OtherScreen initialized")

    def compose(self) -> ComposeResult:
        """Compose the UI elements for the other screen."""
        yield Label("This is another screen.")
        yield Button("Go Back to Input Screen", id="back-button")
        logging.debug("OtherScreen UI composed with label and back button")

    async def on_button_pressed(self, event: Button.Pressed):
        """Handle button press events for navigation."""
        if event.button.id == "back-button":
            logging.info("Back button pressed, navigating to InputBoxScreen")
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
        logging.debug("MultiScreenApp initialized with SessionManager")

    def on_mount(self) -> None:
        """Mount screens when the app starts."""
        self.install_screen(lambda: InputBoxScreen(self.session_manager), name="InputBoxScreen")
        self.install_screen(lambda: OtherScreen(self.session_manager), name="OtherScreen")
        logging.debug("Screens installed: InputBoxScreen and OtherScreen")
        self.push_screen("InputBoxScreen")
        logging.info("Application started with InputBoxScreen")


if __name__ == "__main__":
    logging.info("Starting MultiScreenApp")
    app = MultiScreenApp()
    app.run()
    logging.info("MultiScreenApp has terminated")