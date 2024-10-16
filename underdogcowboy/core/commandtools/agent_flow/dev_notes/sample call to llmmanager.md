

### Developer Note: Asynchronous LLM Calls with `LLMCallManager` in a Textual GUI

The code below demonstrates a clean and scalable implementation of using `LLMCallManager` to handle asynchronous LLM calls within a Textual app. This example highlights a few important architectural decisions:

- **Separation of Concerns**: We keep the logic for making LLM calls (`LLMCallManager`) distinct from the Textual GUI logic. This makes it easy to reuse the LLM call management logic in different contexts without depending on the UI layer.

- **Asynchronous Execution**: The LLM calls are executed asynchronously using `LLMCallManager`, ensuring that the Textual GUI remains responsive and doesn't freeze while the LLM calls are processed in the background.
- **Reusability of Functions**: By separating the LLM function, the manager, and event handling logic, the core functionality can be reused across different parts of the application, making the solution modular and extensible.
- **Non-Blocking GUI**: Even with multiple LLM calls being processed in parallel, the GUI remains fully functional without blocking user interactions or freezing.

In the extended example, we spin off 10 LLM calls asynchronously, each with a unique `input_id`, and process their results as they come in via event handlers. The event-driven architecture allows you to handle multiple LLM calls and display their results without freezing the UI.

#### Key Code Features:
- **Import an LLM Function**: Import a function (like `fake_llm_function`) that interacts with your LLM system.

- **Handle Multiple LLM Calls in a Loop**: Use a loop to spin off multiple asynchronous LLM calls.
- **Event Handling**: Create two asynchronous event handlers (`LLMCallComplete` and `LLMCallError`) that handle LLM responses based on `input_id`, ensuring the right call's response is processed.

--

```python
from textual.app import App
from events.llm_events import LLMCallComplete, LLMCallError
from llm_functions import fake_llm_function
from llm_call_manager import LLMCallManager
import uuid

class MyApp(App):
    def __init__(self):
        super().__init__()
        self.llm_manager = LLMCallManager()  # Initialize LLMCallManager
        self.active_calls = {}  # Store active calls with their input IDs

    def on_mount(self) -> None:
        """Spin off 10 LLM calls when the app starts."""
        for i in range(10):
            input_id = str(uuid.uuid4()) 
            self.active_calls[input_id] = f"LLM Call {i+1}"

            # pre-prompt and post-prompt for each call
            pre_prompt = f"Please analyze the following 
                           configuration for Agent {i+1} and evaluate its clarity."
            post_prompt = f"Conclude the analysis by suggesting
                            improvements to make the configuration clearer."
       # Submit the LLM call with dynamic prompts
            self.llm_manager.submit_llm_call(
                llm_function=fake_llm_function,
                input_value=f"Sample input {i+1}",
                pre_prompt=pre_prompt,
                post_prompt=post_prompt,
                input_id=input_id
            )

    # Event handlers with the @on decorator
    @on(LLMCallComplete)
    async def handle_llm_call_complete(self, message: LLMCallComplete):
        """Handle the LLM call complete event."""
        if message.input_id in self.active_calls:
            # Process the result for the specific input_id
            print(f"LLM Call completed for {self.active_calls[message.input_id]}: {message.result}")
            # Remove the call from active once completed
            del self.active_calls[message.input_id]

    @on(LLMCallError)
    async def handle_llm_call_error(self, message: LLMCallError):
        """Handle the LLM call error event."""
        if message.input_id in self.active_calls:
            # Handle the error for the specific input_id
            print(f"LLM Call failed for {self.active_calls[message.input_id]}: {message.error}")
            # Remove the call from active once error is handled
            del self.active_calls[message.input_id]

# Example usage
app = MyApp()
app.run()
```

### Behind the Scenes:
- **`LLMCallManager`**: Handles task submission and execution in a non-blocking manner, allowing calls to be processed concurrently.
- **Textual GUI Integration**: The `LLMCallManager` posts events (`LLMCallComplete` and `LLMCallError`) that are handled by the Textual app, ensuring smooth UI updates without freezing.

This design ensures that the LLM function logic, asynchronous processing, and event handling are clearly separated, enabling a responsive and reusable architecture for handling LLM calls in a Textual-based GUI.

---
