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
logging.basicConfig(
    filename='app.log',
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class LLMCallManager:

    """Manages asynchronous calls using a ThreadPoolExecutor."""
    def __init__(self, max_workers=5):
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        logging.debug("LLMCallManager initialized with ThreadPoolExecutor")

    async def run_llm_call(self, llm_function, *args):
        """Run a function asynchronously in a thread pool."""
        logging.debug(f"Running function {llm_function.__name__} with args: {args}")
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self.executor, llm_function, *args)


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

    #loading-indicator, #loading-scales-indicator {
        margin: 1 2;
        visibility: hidden;
    }

    #loading-indicator.visible, #loading-scales-indicator.visible {
        visibility: visible;
    }
    """

    def __init__(self):
        super().__init__()
        self.llm_call_manager = LLMCallManager()
        self.categories = [("create_initial", "Create Initial Categories")]
        self.selected_category = None
        self.selected_scale = None
        self.current_scales = []  # Will store the scales for the selected category
        self.all_categories = MOCK_CATEGORIES.copy()  # Store initial categories
        logging.debug("Initialized with Create Initial Categories")

    def compose(self) -> ComposeResult:
        yield Header()
        self.select = Select(self.categories, id="category-select")
        yield self.select

        # Loading indicator for categories
        self.loading_indicator = Static("  Loading categories...", id="loading-indicator")
        yield self.loading_indicator

        # Editable input for category name
        self.input_box = Input(placeholder="Rename selected category", id="category-input")
        self.input_box.visible = False
        yield self.input_box

        # Editable TextArea for the category description
        self.description_area = TextArea("", id="category-description-area")
        self.description_area.visible = False
        yield self.description_area

        # Loading indicator for scales
        self.loading_scales_indicator = Static("  Loading scales...", id="loading-scales-indicator")
        yield self.loading_scales_indicator

        # Scale select box - initialized with "Load Scales"
        self.scale_select = Select([("load_scales", "Load Scales")], id="scale-select")
        self.scale_select.visible = True  # Always visible, but only populated upon user action
        yield self.scale_select

        # Editable input for scale name
        self.scale_input_box = Input(placeholder="Rename selected scale", id="scale-input")
        self.scale_input_box.visible = False  # Initially hidden, shown after scale selection
        yield self.scale_input_box

        # Editable TextArea for the scale description
        self.scale_description_area = TextArea("", id="scale-description-area")
        self.scale_description_area.visible = False  # Initially hidden
        yield self.scale_description_area

    async def show_loading_indicator(self, indicator_id: str):
        """Show the specified loading indicator."""
        indicator = self.query_one(f"#{indicator_id}", Static)
        indicator.add_class("visible")
        self.refresh()

    async def hide_loading_indicator(self, indicator_id: str):
        """Hide the specified loading indicator."""
        indicator = self.query_one(f"#{indicator_id}", Static)
        indicator.remove_class("visible")
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

    @on(Select.Changed, "#category-select")
    async def category_changed(self, event: Select.Changed) -> None:
        selected_value = event.value
        logging.info(f"Category Select changed: {selected_value}")

        if selected_value == Select.BLANK:
            logging.info("No category selection made (BLANK)")
            return

        if selected_value == "Create Initial Categories":
            # Show loading indicator and start async retrieval of categories
            self.select.set_options([("waiting", "Waiting for categories...")])
            await self.show_loading_indicator("loading-indicator")  # Show category loading indicator

            # Asynchronously retrieve categories
            asyncio.create_task(self.retrieve_categories())

        elif selected_value == "Refresh All":
            # Show loading indicator and simulate async retrieval of new categories
            self.select.set_options([("waiting", "Refreshing categories...")])
            await self.show_loading_indicator("loading-indicator")  # Show category loading indicator

            # Asynchronously retrieve new categories
            asyncio.create_task(self.retrieve_new_categories())

        else:
            # Handle category selection
            self.selected_category = selected_value
            self.input_box.value = selected_value
            self.input_box.visible = True

            # Find the description of the selected category
            selected_category_data = next(
                (cat for cat in self.all_categories if cat['name'] == selected_value), None
            )
            if selected_category_data:
                self.description_area.text = selected_category_data["description"]
                self.description_area.visible = True
                self.description_area.refresh()
                logging.info(f"Category selected: {selected_value}, description displayed.")

                # Reset the scale select box to "Load Scales"
                self.scale_select.set_options([("load_scales", "Load Scales")])
                self.scale_select.value = "Load Scales"

                # Hide scale-related widgets
                self.scale_input_box.visible = False
                self.scale_description_area.visible = False

            else:
                logging.error(f"Selected category '{selected_value}' not found.")
                self.description_area.text = "Category not found."
                self.description_area.visible = True

        self.refresh()

    @on(Select.Changed, "#scale-select")
    async def scale_changed(self, event: Select.Changed) -> None:
        selected_scale = event.value
        logging.info(f"Scale Select changed: {selected_scale}")

        if selected_scale == Select.BLANK:
            logging.info("No scale selection made (BLANK)")
            return

        if selected_scale == "load_scales":
            # Ensure a category is selected before loading scales
            if not self.selected_category:
                logging.warning("No category selected. Please select a category first.")
                # Optionally, display a message to the user
                return

            # Show loading indicator for scales
            self.scale_select.set_options([("loading", "Loading scales...")])
            await self.show_loading_indicator("loading-scales-indicator")

            # Asynchronously retrieve scales for the selected category
            asyncio.create_task(self.retrieve_scales())

        elif selected_scale == "loading":
            # Currently loading scales; do nothing
            logging.info("Scale selection is currently loading...")
            return

        else:
            # Handle scale selection
            self.selected_scale = selected_scale

            # Find the description of the selected scale
            selected_scale_data = next(
                (scale for scale in self.current_scales if scale['name'] == selected_scale), None
            )
            if selected_scale_data:
                self.scale_description_area.text = selected_scale_data["description"]
                self.scale_description_area.visible = True

                # Show input box for renaming the scale
                self.scale_input_box.value = selected_scale
                self.scale_input_box.visible = True
                logging.info(f"Scale selected: {selected_scale}, description displayed, input box for renaming shown.")
            else:
                logging.error(f"Selected scale '{selected_scale}' not found.")
                self.scale_description_area.text = "Scale not found."
                self.scale_description_area.visible = True

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
        except Exception as e:
            logging.error(f"Error retrieving categories: {e}")
            self.select.set_options([("error", "Error loading categories")])
        finally:
            await self.hide_loading_indicator("loading-indicator")
            self.refresh()

    async def retrieve_new_categories(self):
        """Simulate retrieval of new categories asynchronously for Refresh All."""
        try:
            new_categories = await self.llm_call_manager.run_llm_call(self.simulate_new_categories)
            self.all_categories = new_categories  # Replace with the new categories after refresh
            self.categories = [("refresh_all", "Refresh All")] + [(cat['name'], cat['name']) for cat in self.all_categories]
            self.select.set_options(self.categories)
            self.select.value = new_categories[0]['name']  # Automatically select the first new category
            logging.debug(f"New categories retrieved: {new_categories}")
        except Exception as e:
            logging.error(f"Error retrieving new categories: {e}")
            self.select.set_options([("error", "Error loading new categories")])
        finally:
            await self.hide_loading_indicator("loading-indicator")
            self.refresh()

    async def retrieve_scales(self):
        """Simulate retrieval of scales asynchronously based on the selected category."""
        try:
            # Simulate scale retrieval delay
            await asyncio.sleep(2)  # Shorter delay for scales
            # Find scales for the selected category
            selected_category_data = next(
                (cat for cat in self.all_categories if cat['name'] == self.selected_category), None
            )
            if selected_category_data:
                self.current_scales = selected_category_data["scale"]
                if self.current_scales:
                    # Populate the scale select box with the retrieved scales
                    self.scale_select.set_options([(scale['name'], scale['name']) for scale in self.current_scales])
                    self.scale_select.value = self.current_scales[0]['name']  # Automatically select the first scale
                    logging.debug(f"Scales retrieved: {self.current_scales}")
                else:
                    self.scale_select.set_options([("no_scales", "No scales available")])
                    self.scale_select.value = "No scales available"
                    logging.debug("No scales found for the selected category.")
            else:
                logging.error(f"Selected category '{self.selected_category}' not found while retrieving scales.")
                self.scale_select.set_options([("error", "Error loading scales")])
        except Exception as e:
            logging.error(f"Error retrieving scales: {e}")
            self.scale_select.set_options([("error", "Error loading scales")])
        finally:
            await self.hide_loading_indicator("loading-scales-indicator")
            self.refresh()

    @on(Input.Submitted, "#category-input")
    def category_input_submitted(self, event: Input.Submitted) -> None:
        # Handle category renaming
        if self.selected_category:
            new_name = event.value.strip()
            if not new_name:
                logging.warning("Attempted to rename category to an empty string.")
                return

            logging.info(f"Renaming category '{self.selected_category}' to '{new_name}'")
            for cat in self.all_categories:
                if cat['name'] == self.selected_category:
                    cat['name'] = new_name
                    break

            # Update the categories list
            self.categories = [("refresh_all", "Refresh All")] + [(cat['name'], cat['name']) for cat in self.all_categories]
            self.select.set_options(self.categories)
            self.select.value = new_name

            # Update selection variables
            self.selected_category = new_name
            self.input_box.visible = False
            self.description_area.visible = False
            # Reset the scale select box to "Load Scales"
            self.scale_select.set_options([("load_scales", "Load Scales")])
            self.scale_select.value = "Load Scales"
            # Hide scale-related widgets
            self.scale_input_box.visible = False
            self.scale_description_area.visible = False
            logging.debug(f"Category renamed to '{new_name}'")
            self.refresh()

    @on(Input.Submitted, "#scale-input")
    def scale_input_submitted(self, event: Input.Submitted) -> None:
        # Handle scale renaming
        if self.selected_scale and self.selected_category:
            new_scale_name = event.value.strip()
            if not new_scale_name:
                logging.warning("Attempted to rename scale to an empty string.")
                return

            logging.info(f"Renaming scale '{self.selected_scale}' to '{new_scale_name}' in category '{self.selected_category}'")
            for scale in self.current_scales:
                if scale['name'] == self.selected_scale:
                    scale['name'] = new_scale_name
                    break

            # Update the scale select options
            self.scale_select.set_options([(scale['name'], scale['name']) for scale in self.current_scales])
            self.scale_select.value = new_scale_name

            # Update selection variables
            self.selected_scale = new_scale_name
            self.scale_input_box.visible = False
            self.scale_description_area.visible = False
            logging.debug(f"Scale renamed to '{new_scale_name}'")
            self.refresh()

    @on(TextArea.Changed, "#category-description-area")
    def category_description_changed(self, event: TextArea.Changed) -> None:
        # Handle category description updates
        if self.selected_category:
            # Access the updated text via event.text_area.document.text
            new_description = event.text_area.document.text.strip()
            logging.info(f"Updating description for category '{self.selected_category}'")
            for cat in self.all_categories:
                if cat['name'] == self.selected_category:
                    cat['description'] = new_description
                    break
            logging.debug(f"Category '{self.selected_category}' description updated.")
            self.refresh()

    @on(TextArea.Changed, "#scale-description-area")
    def scale_description_changed(self, event: TextArea.Changed) -> None:
        # Handle scale description updates
        if self.selected_scale and self.selected_category:
            # Access the updated text via event.text_area.document.text
            new_description = event.text_area.document.text.strip()
            logging.info(f"Updating description for scale '{self.selected_scale}' in category '{self.selected_category}'")
            for scale in self.current_scales:
                if scale['name'] == self.selected_scale:
                    scale['description'] = new_description
                    break
            logging.debug(f"Scale '{self.selected_scale}' description updated.")
            self.refresh()

if __name__ == "__main__":
    logging.info("Starting SelectApp")
    app = SelectApp()
    app.run()
    logging.info("SelectApp has terminated")
