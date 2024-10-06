import logging
import asyncio
from concurrent.futures import ThreadPoolExecutor
from textual import on
from textual.app import App, ComposeResult
from textual.widgets import Header, Select, Input, Static

# Mockup categories that can be refreshed
MOCK_CATEGORIES = ["Category 1", "Category 2", "Category 3", "Category 4", "Category 5"]

# Configure the logging to log to a file only
logging.basicConfig(filename='app.log', level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

class LLMCallManager:
    """Manages asynchronous calls using a ThreadPoolExecutor."""
    def __init__(self, max_workers=5):
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        logging.debug("LLMCallManager initialized with ThreadPoolExecutor")

    async def run_llm_call(self, llm_function, *args):
        """Run a function asynchronously in a thread pool."""
        logging.debug(f"Running function {llm_function.__name__} with args: {args}")
        return await asyncio.get_event_loop().run_in_executor(self.executor, llm_function, *args)

class SelectApp(App):
    CSS = """
    Screen {
        align: center top;  /* Align content to the top of the screen */
    }

    Select {
        width: 60;
        margin: 2;
    }

    Input {
        width: 60;
        margin: 2;
    }

    #loading-indicator {
        margin-top: 1;
        visibility: hidden;  /* Hidden by default */
    }

    #loading-indicator.visible {
        visibility: visible;  /* Make the indicator visible */
    }
    """

    def __init__(self):
        super().__init__()
        self.llm_call_manager = LLMCallManager()
        self.categories = [("create_initial", "Create Initial Categories")]
        self.selected_category = None
        logging.debug("Initialized with Create Initial Categories")

    def compose(self) -> ComposeResult:
        yield Header()
        self.select = Select(self.categories)
        yield self.select
        # Add the LoadingIndicator, hidden by default
        self.loading_indicator = Static("    Loading...", id="loading-indicator")
        yield self.loading_indicator
        self.input_box = Input(placeholder="Rename selected category")
        self.input_box.visible = False
        yield self.input_box

    async def show_loading_indicator(self):
        """Show the loading indicator."""
        self.loading_indicator.add_class("visible")
        self.refresh()

    async def hide_loading_indicator(self):
        """Hide the loading indicator."""
        self.loading_indicator.remove_class("visible")
        self.refresh()

    def simulate_category_retrieval(self):
        """Simulate a long-running category retrieval (mock for LLM call)."""
        import time
        logging.debug("Simulating category retrieval...")
        time.sleep(5)  # Simulate network delay
        return ["Category 1", "Category 2", "Category 3", "Category 4", "Category 5"]

    @on(Select.Changed)
    async def select_changed(self, event: Select.Changed) -> None:
        selected_value = event.value
        logging.info(f"Select changed: {selected_value}")

        if selected_value == Select.BLANK:
            logging.info("No selection made (BLANK)")
            return

        if selected_value == "Create Initial Categories":
            # Show "Loading..." and start async retrieval of categories
            self.select.set_options([("waiting", "Waiting for categories...")])
            await self.show_loading_indicator()  # Show the loading indicator

            # Use the LLMCallManager to simulate category retrieval asynchronously
            asyncio.create_task(self.retrieve_categories())

        elif selected_value == "Refresh All":
            # Fetch some new categories (simulate)
            new_categories = ["Category 6", "Category 7", "Category 8", "Category 9", "Category 10"]
            self.categories = [("refresh_all", "Refresh All")] + [(category, category) for category in new_categories]
            self.select.set_options(self.categories)
            logging.debug("Categories refreshed with new mock categories")

        else:
            self.selected_category = selected_value
            self.input_box.value = selected_value
            self.input_box.visible = True
            logging.info(f"Category selected for renaming: {selected_value}")

        self.refresh()

    async def retrieve_categories(self):
        """Simulate retrieval of categories asynchronously."""
        try:
            categories = await self.llm_call_manager.run_llm_call(self.simulate_category_retrieval)
            self.categories = [("refresh_all", "Refresh All")] + [(category, category) for category in categories]
            self.select.set_options(self.categories)
            self.select.value = categories[0]  # Automatically select the first category
            logging.debug(f"Categories retrieved: {categories}")
        finally:
            await self.hide_loading_indicator()

    @on(Input.Submitted)
    def input_submitted(self, event: Input.Submitted) -> None:
        if self.selected_category:
            new_name = event.value
            logging.info(f"Renaming category {self.selected_category} to {new_name}")
            for i, (key, label) in enumerate(self.categories):
                if label == self.selected_category:
                    self.categories[i] = (new_name, new_name)
                    break
            self.select.set_options(self.categories)
            self.input_box.visible = False
            self.selected_category = None
            self.refresh()
            logging.debug(f"Category renamed to {new_name}")

if __name__ == "__main__":
    logging.info("Starting SelectApp")
    app = SelectApp()
    app.run()
    logging.info("SelectApp has terminated")
