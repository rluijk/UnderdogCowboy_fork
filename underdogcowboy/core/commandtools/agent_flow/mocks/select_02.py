import logging
import asyncio
from concurrent.futures import ThreadPoolExecutor
from textual import on
from textual.app import App, ComposeResult
from textual.widgets import Header, Select, Input, Static, TextArea

# Mockup categories extended with description and a scale of 1-5
MOCK_CATEGORIES = [
    {
        "name": "Category 1",
        "description": "This is the description for Category 1.",
        "scale": [
            {"name": "Scale 1", "description": "This is scale 1 description."},
            {"name": "Scale 2", "description": "This is scale 2 description."},
            {"name": "Scale 3", "description": "This is scale 3 description."},
            {"name": "Scale 4", "description": "This is scale 4 description."},
            {"name": "Scale 5", "description": "This is scale 5 description."},
        ],
    },
    {
        "name": "Category 2",
        "description": "This is the description for Category 2.",
        "scale": [
            {"name": "Scale 1", "description": "This is scale 1 description."},
            {"name": "Scale 2", "description": "This is scale 2 description."},
            {"name": "Scale 3", "description": "This is scale 3 description."},
            {"name": "Scale 4", "description": "This is scale 4 description."},
            {"name": "Scale 5", "description": "This is scale 5 description."},
        ],
    },
]

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
        align: center top;
    }

    Select {
        width: 60;
        margin: 1 2;
    }

    Input {
        width: 60;
        margin: 1 2;
    }

    TextArea {
        width: 60;
        height: 12;
        margin: 1 2;
    }

    #loading-indicator {
        margin: 1 2;
        visibility: hidden;
    }

    #loading-indicator.visible {
        visibility: visible;
    }
    """

    def __init__(self):
        super().__init__()
        self.llm_call_manager = LLMCallManager()
        self.categories = [("create_initial", "Create Initial Categories")]
        self.selected_category = None
        self.selected_description = None
        self.all_categories = MOCK_CATEGORIES.copy()  # Store initial categories
        logging.debug("Initialized with Create Initial Categories")

    def compose(self) -> ComposeResult:
        yield Header()
        self.select = Select(self.categories)
        yield self.select
        # Add the LoadingIndicator, hidden by default
        self.loading_indicator = Static("  Loading...", id="loading-indicator")
        yield self.loading_indicator
        self.input_box = Input(placeholder="Rename selected category")
        self.input_box.visible = False
        yield self.input_box
        self.description_area = TextArea("", id="description-area")  # Editable TextArea for the description
        yield self.description_area

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
        return MOCK_CATEGORIES

    def simulate_new_categories(self):
        """Simulate the retrieval of new categories for Refresh All."""
        import time
        logging.debug("Simulating new categories for refresh...")
        time.sleep(5)  # Simulate network delay
        return [
            {
                "name": "Category 3",
                "description": "This is the description for Category 3.",
                "scale": [
                    {"name": "Scale 1", "description": "This is scale 1 description."},
                    {"name": "Scale 2", "description": "This is scale 2 description."},
                    {"name": "Scale 3", "description": "This is scale 3 description."},
                    {"name": "Scale 4", "description": "This is scale 4 description."},
                    {"name": "Scale 5", "description": "This is scale 5 description."},
                ],
            },
            {
                "name": "Category 4",
                "description": "This is the description for Category 4.",
                "scale": [
                    {"name": "Scale 1", "description": "This is scale 1 description."},
                    {"name": "Scale 2", "description": "This is scale 2 description."},
                    {"name": "Scale 3", "description": "This is scale 3 description."},
                    {"name": "Scale 4", "description": "This is scale 4 description."},
                    {"name": "Scale 5", "description": "This is scale 5 description."},
                ],
            },
        ]

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
            # Show "Loading..." and simulate the async retrieval of new categories
            self.select.set_options([("waiting", "Refreshing categories...")])
            await self.show_loading_indicator()

            # Retrieve new categories asynchronously
            asyncio.create_task(self.retrieve_new_categories())

        else:
            self.selected_category = selected_value
            self.input_box.value = selected_value
            self.input_box.visible = True

            # Find the description of the selected category in the merged list
            self.selected_description = next((cat['description'] for cat in self.all_categories if cat['name'] == selected_value), "")
            self.description_area.text = self.selected_description  # Set description in the editable TextArea
            logging.info(f"Category selected for renaming: {selected_value}, Description: {self.selected_description}")

        self.refresh()

    async def retrieve_categories(self):
        """Simulate retrieval of categories asynchronously."""
        try:
            categories = await self.llm_call_manager.run_llm_call(self.simulate_category_retrieval)
            self.all_categories = categories  # Replace with initial categories
            self.categories = [("refresh_all", "Refresh All")] + [(cat['name'], cat['name']) for cat in categories]
            self.select.set_options(self.categories)
            self.select.value = categories[0]['name']  # Automatically select the first category
            logging.debug(f"Categories retrieved: {categories}")
        finally:
            await self.hide_loading_indicator()

    async def retrieve_new_categories(self):
        """Simulate retrieval of new categories asynchronously for Refresh All."""
        try:
            new_categories = await self.llm_call_manager.run_llm_call(self.simulate_new_categories)
            self.all_categories = new_categories  # Replace with the new categories after refresh
            self.categories = [("refresh_all", "Refresh All")] + [(cat['name'], cat['name']) for cat in self.all_categories]
            self.select.set_options(self.categories)
            self.select.value = new_categories[0]['name']  # Automatically select the first new category
            logging.debug(f"New categories retrieved: {new_categories}")
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
