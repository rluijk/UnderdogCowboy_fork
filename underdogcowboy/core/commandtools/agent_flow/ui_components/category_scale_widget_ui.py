import logging
import asyncio

from concurrent.futures import ThreadPoolExecutor

from textual import on
from textual.app import App, ComposeResult
from textual.containers import Vertical, Horizontal
from textual.widgets import Label,Header, Select, Input, Static, TextArea, Button
from textual.message import Message

# Configure the logging to log to a file only
logging.basicConfig(
    filename='category_scale_widget.log',
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

    def simulate_category_retrieval(self):
        """Simulate a long-running category retrieval (mock for LLM call)."""
        import time
        logging.debug("Simulating category retrieval...")
        time.sleep(2)  # Simulate network delay
        return [
            {
                "name": "Category 1",
                "description": "This is the description for Category 1.",
                "scale": [],  # Empty scales
            },
            {
                "name": "Category 2",
                "description": "This is the description for Category 2.",
                "scale": [
                    {"name": "Scale 1", "description": "This is scale 1 description."},
                    {"name": "Scale 2", "description": "This is scale 2 description."},
                ],
            },
        ]

    def simulate_new_categories(self):
        """Simulate the retrieval of new categories for Refresh All."""
        import time
        logging.debug("Simulating new categories for refresh...")
        time.sleep(2)  # Simulate network delay
        return [
            {
                "name": "Category 3",
                "description": "This is the description for Category 3.",
                "scale": [],  # Empty scales
            },
            {
                "name": "Category 4",
                "description": "This is the description for Category 4.",
                "scale": [
                    {"name": "Scale A", "description": "This is scale A description."},
                    {"name": "Scale B", "description": "This is scale B description."},
                ],
            },
        ]

    def simulate_scale_retrieval(self, category_name):
        """Simulate a long-running scale retrieval for a category (mock for LLM call)."""
        import time
        logging.debug(f"Simulating scale retrieval for category '{category_name}'...")
        time.sleep(2)  # Simulate network delay
        # Return some mock scales for the category
        return [
            {"name": f"{category_name} Scale 1", "description": f"This is the description for {category_name} Scale 1."},
            {"name": f"{category_name} Scale 2", "description": f"This is the description for {category_name} Scale 2."},
        ]

class CategorySelected(Message):
    """Custom message to indicate a category has been selected."""
    def __init__(self, sender, category_name: str):
        super().__init__()
        self.sender = sender
        self.category_name = category_name

class SelectCategoryWidget(Static):
    """Widget for the UI components of categories."""
    def __init__(self, llm_call_manager):
        super().__init__()
        self.selected_category = None  # Initialize to track the selected category
        self.llm_call_manager = llm_call_manager         

        self.select = Select(
            options=[("create_initial", "Create Initial Categories")],
            id="category-select"
        )
        self.loading_indicator = Static(
            "  Loading categories...", 
            id="loading-indicator"
        )
        self.input_box = Input(
            placeholder="Rename selected category", 
            id="category-input"
        )
        self.description_area = TextArea(
            "", 
            id="category-description-area"
        )
        # Initialize buttons
        self.refresh_title_button = Button(
            "Refresh Title", 
            id="refresh-title-button"
        )
        self.refresh_description_button = Button(
            "Refresh Description", 
            id="refresh-description-button"
        )
        self.refresh_both_button = Button(
            "Refresh Both", 
            id="refresh-both-button"
        )
        
        self.lbl_text =  Label("Modify Directly or use buttons for agent assistance", id="lbl_text") 

        # Initially hide certain components, including buttons
        self.loading_indicator.visible = False
        self.input_box.visible = False
        self.description_area.visible = False
        self.refresh_title_button.visible = False
        self.refresh_description_button.visible = False
        self.refresh_both_button.visible = False
        self.lbl_text.visible = False
        
    def compose(self) -> ComposeResult:
        yield self.select
        yield self.loading_indicator
        with Vertical(id="edit_container"):
            yield self.lbl_text
            yield self.input_box
            yield self.description_area
            # Create a horizontal container for the buttons
            btn_container = Horizontal(id="button-container")
            with btn_container:
                yield self.refresh_title_button
                yield self.refresh_description_button
                yield self.refresh_both_button

    async def refresh_title(self):
        """Function to refresh the title using LLMCallManager."""
        if self.selected_category:  # Ensure there's a category selected
            # Call the LLM to retrieve new title data (mockup method)
            title_data = await self.llm_call_manager.run_llm_call(
                self.llm_call_manager.simulate_scale_retrieval, self.selected_category
            )
            # Update the input box with the new title data (simulated)
            self.input_box.value = title_data[0]['name']  # Assuming the first element holds the title info
            self.input_box.refresh()
    
    async def refresh_description(self):
        """Function to refresh the description using LLMCallManager."""
        if self.selected_category:
            # Call the LLM to retrieve new description data (mockup method)
            description_data = await self.llm_call_manager.run_llm_call(
                self.llm_call_manager.simulate_scale_retrieval, self.selected_category
            )
            # Update the description area with the new description
            self.description_area.value = description_data[0]['description']
            self.description_area.refresh()
    
    async def refresh_both(self):
        """Function to refresh both title and description."""
        await self.refresh_title()
        await self.refresh_description()

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events."""
        button_id = event.button.id
        if button_id == "refresh-title-button":
            await self.refresh_title()  # Ensure this is awaited
        elif button_id == "refresh-description-button":
            await self.refresh_description()
        elif button_id == "refresh-both-button":
            await self.refresh_both()

    def show_buttons(self):
        """Utility method to make buttons visible."""
        self.refresh_title_button.visible = True
        self.refresh_description_button.visible = True
        self.refresh_both_button.visible = True
        self.lbl_text.visible = True

    def hide_buttons(self):
        """Utility method to hide buttons."""
        self.refresh_title_button.visible = False
        self.refresh_description_button.visible = False
        self.refresh_both_button.visible = False
        self.lbl_text.visible = False

class SelectScaleWidget(Static):
    """Widget for the UI components of scales."""
    def __init__(self):
        super().__init__()
        self.create_scales_button = Button("Create Initial Scales", id="create-scales-button")
        self.scale_select = Select([], id="scale-select")
        self.loading_indicator = Static("  Loading scales...", id="scale-loading-indicator")
        self.scale_input_box = Input(placeholder="Rename selected scale", id="scale-input")
        self.scale_description_area = TextArea("", id="scale-description-area")
        
        self.create_scales_button.visible = False
        self.scale_select.visible = False
        self.loading_indicator.visible = False
        self.scale_input_box.visible = False
        self.scale_description_area.visible = False

    def compose(self) -> ComposeResult:
        yield self.create_scales_button
        yield self.scale_select
        yield self.loading_indicator
        yield self.scale_input_box
        yield self.scale_description_area

class CategoryWidget(Static):
    """Widget for managing categories."""
    def __init__(self, llm_call_manager, all_categories, id=None):
        super().__init__(id=id)
        self.selected_category = None
        self.llm_call_manager = llm_call_manager
        self.all_categories = all_categories  # Datastructure passed via init
        self.selected_category = None
        self.category_components = SelectCategoryWidget(self.llm_call_manager)

    def compose(self) -> ComposeResult:
        yield self.category_components

    @on(Select.Changed, "#category-select")
    async def category_changed(self, event: Select.Changed) -> None:
        selected_value = event.value
        logging.info(f"Category Select changed: {selected_value}")

        self.selected_category = selected_value  
        # Ensure the category selection is propagated to SelectCategoryWidget
        self.category_components.selected_category = selected_value


        if selected_value == Select.BLANK:
            logging.info("No category selection made (BLANK)")
            self.category_components.hide_buttons()  # Hide buttons if no selection
            return

        if selected_value == "Create Initial Categories":
            self.category_components.select.set_options([("waiting", "Waiting for categories...")])
            await self.show_loading_indicator()
            self.category_components.hide_buttons()  # Hide buttons while loading
            asyncio.create_task(self.retrieve_categories())

        elif selected_value == "Refresh All":
            self.category_components.select.set_options([("waiting", "Refreshing categories...")])
            await self.show_loading_indicator()
            self.category_components.hide_buttons()  # Hide buttons while refreshing
            asyncio.create_task(self.retrieve_new_categories())

        else:
            self.selected_category = selected_value
            self.category_components.input_box.value = selected_value
            self.category_components.input_box.visible = True

            selected_category_data = next(
                (cat for cat in self.all_categories if cat['name'] == selected_value), None
            )
            if selected_category_data:
                self.category_components.description_area.text = selected_category_data["description"]
                self.category_components.description_area.visible = True
                self.category_components.description_area.refresh()

                self.category_components.show_buttons()  # Show buttons when a valid category is selected
                self.post_message(CategorySelected(self, self.selected_category))
            else:
                self.category_components.description_area.text = "Category not found."
                self.category_components.description_area.visible = True
                self.category_components.show_buttons()  # Optionally show buttons even if category not found

        self.refresh()

    async def show_loading_indicator(self):
        self.category_components.loading_indicator.visible = True
        self.refresh()

    async def hide_loading_indicator(self):
        self.category_components.loading_indicator.visible = False
        self.refresh()

    async def retrieve_categories(self):
        try:
            categories = await self.llm_call_manager.run_llm_call(self.llm_call_manager.simulate_category_retrieval)
            self.all_categories[:] = categories
            self.category_components.select.set_options([("refresh_all", "Refresh All")] + [(cat['name'], cat['name']) for cat in categories])
            self.category_components.select.value = categories[0]['name']
            # After successfully retrieving categories, buttons can be shown
            self.category_components.show_buttons()
        except Exception as e:
            logging.error(f"Error retrieving categories: {e}")
            self.category_components.select.set_options([("error", "Error loading categories")])
            self.category_components.hide_buttons()  # Hide buttons on error
        finally:
            await self.hide_loading_indicator()
            self.refresh()

    async def retrieve_new_categories(self):
        try:
            new_categories = await self.llm_call_manager.run_llm_call(self.llm_call_manager.simulate_new_categories)
            self.all_categories[:] = new_categories
            self.category_components.select.set_options([("refresh_all", "Refresh All")] + [(cat['name'], cat['name']) for cat in self.all_categories])
            self.category_components.select.value = new_categories[0]['name']
            # After successfully retrieving new categories, buttons can be shown
            self.category_components.show_buttons()
        except Exception as e:
            logging.error(f"Error retrieving new categories: {e}")
            self.category_components.select.set_options([("error", "Error loading new categories")])
            self.category_components.hide_buttons()  # Hide buttons on error
        finally:
            await self.hide_loading_indicator()
            self.refresh()

    @on(Input.Submitted, "#category-input")
    def category_input_submitted(self, event: Input.Submitted) -> None:
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

            self.category_components.select.set_options([("refresh_all", "Refresh All")] + [(cat['name'], cat['name']) for cat in self.all_categories])
            self.category_components.select.value = new_name

            self.selected_category = new_name
            self.category_components.input_box.visible = False
            self.category_components.description_area.visible = False
            self.refresh()

    @on(TextArea.Changed, "#category-description-area")
    def category_description_changed(self, event: TextArea.Changed) -> None:
        if self.selected_category:
            new_description = event.text_area.document.text.strip()
            logging.info(f"Updating description for category '{self.selected_category}'")
            for cat in self.all_categories:
                if cat['name'] == self.selected_category:
                    cat['description'] = new_description
                    break
            self.refresh()

class ScaleWidget(Static):
    """Widget for managing scales within a selected category."""
    def __init__(self, llm_call_manager, all_categories, id=None):
        super().__init__(id=id)
        self.llm_call_manager = llm_call_manager
        self.all_categories = all_categories  # Reference to the categories data structure
        self.selected_category = None
        self.current_scales = []
        self.selected_scale = None
        self.scale_components = SelectScaleWidget()

    def compose(self) -> ComposeResult:
        yield self.scale_components

    def update_scales(self, selected_category_name):
        """Update scales based on the selected category."""
        self.selected_category = selected_category_name
        selected_category_data = next(
            (cat for cat in self.all_categories if cat['name'] == selected_category_name), None
        )
        if selected_category_data:
            self.current_scales = selected_category_data.get("scale", [])
            if self.current_scales:
                # Populate the scale select widget
                self.scale_components.scale_select.set_options([(scale['name'], scale['name']) for scale in self.current_scales])
                self.scale_components.scale_select.value = self.current_scales[0]['name']
                self.scale_components.scale_select.visible = True
                self.scale_components.scale_input_box.visible = True
                self.scale_components.scale_description_area.visible = True
                self.scale_components.create_scales_button.visible = False
                # Display the first scale's details
                self.display_scale_details(self.current_scales[0]['name'])
            else:
                # No scales available
                self.scale_components.scale_select.set_options([])
                self.scale_components.scale_select.visible = False
                self.scale_components.scale_input_box.visible = False
                self.scale_components.scale_description_area.visible = False
                self.scale_components.create_scales_button.visible = True  # Show the button to create scales
        else:
            # Category not found
            self.current_scales = []
            self.scale_components.scale_select.set_options([])
            self.scale_components.scale_select.visible = False
            self.scale_components.scale_input_box.visible = False
            self.scale_components.scale_description_area.visible = False
            self.scale_components.create_scales_button.visible = False
        self.refresh()

    @on(Button.Pressed, "#create-scales-button")
    async def create_scales_pressed(self, event: Button.Pressed) -> None:
        logging.info(f"Creating initial scales for category '{self.selected_category}'")
        self.scale_components.create_scales_button.visible = False
        self.scale_components.loading_indicator.visible = True
        self.refresh()
        asyncio.create_task(self.retrieve_scales())

    async def retrieve_scales(self):
        """Retrieve scales via LLMCallManager for the selected category."""
        try:
            scales = await self.llm_call_manager.run_llm_call(
                self.llm_call_manager.simulate_scale_retrieval,
                self.selected_category
            )
            for cat in self.all_categories:
                if cat['name'] == self.selected_category:
                    cat['scale'] = scales
                    break
            self.current_scales = scales
            self.scale_components.scale_select.set_options([(scale['name'], scale['name']) for scale in scales])
            self.scale_components.scale_select.value = scales[0]['name']
            self.scale_components.scale_select.visible = True
            self.scale_components.scale_input_box.visible = True
            self.scale_components.scale_description_area.visible = True
            self.scale_components.create_scales_button.visible = False
            logging.debug(f"Scales retrieved for category '{self.selected_category}': {scales}")
            self.display_scale_details(scales[0]['name'])
        except Exception as e:
            logging.error(f"Error retrieving scales for category '{self.selected_category}': {e}")
        finally:
            self.scale_components.loading_indicator.visible = False
            self.refresh()

    def display_scale_details(self, scale_name):
        """Display details of the selected scale."""
        self.selected_scale = scale_name
        selected_scale_data = next(
            (scale for scale in self.current_scales if scale['name'] == scale_name), None
        )
        if selected_scale_data:
            self.scale_components.scale_input_box.value = selected_scale_data['name']
            self.scale_components.scale_description_area.text = selected_scale_data['description']
            self.scale_components.scale_input_box.visible = True
            self.scale_components.scale_description_area.visible = True
        else:
            self.scale_components.scale_input_box.visible = False
            self.scale_components.scale_description_area.visible = False
        self.refresh()

    @on(Select.Changed, "#scale-select")
    async def scale_changed(self, event: Select.Changed) -> None:
        selected_scale = event.value
        logging.info(f"Scale Select changed: {selected_scale}")
        if selected_scale == Select.BLANK:
            logging.info("No scale selection made (BLANK)")
            return
        self.display_scale_details(selected_scale)

    @on(Input.Submitted, "#scale-input")
    def scale_input_submitted(self, event: Input.Submitted) -> None:
        if self.selected_scale and self.selected_category:
            new_name = event.value.strip()
            if not new_name:
                logging.warning("Attempted to rename scale to an empty string.")
                return
            logging.info(f"Renaming scale '{self.selected_scale}' to '{new_name}' in category '{self.selected_category}'")
            for scale in self.current_scales:
                if scale['name'] == self.selected_scale:
                    scale['name'] = new_name
                    break
            for cat in self.all_categories:
                if cat['name'] == self.selected_category:
                    cat['scale'] = self.current_scales
                    break
            self.scale_components.scale_select.set_options([(scale['name'], scale['name']) for scale in self.current_scales])
            self.scale_components.scale_select.value = new_name
            self.selected_scale = new_name
            self.refresh()

    @on(TextArea.Changed, "#scale-description-area")
    def scale_description_changed(self, event: TextArea.Changed) -> None:
        if self.selected_scale and self.selected_category:
            new_description = event.text_area.document.text.strip()
            logging.info(f"Updating description for scale '{self.selected_scale}' in category '{self.selected_category}'")
            for scale in self.current_scales:
                if scale['name'] == self.selected_scale:
                    scale['description'] = new_description
                    break
            for cat in self.all_categories:
                if cat['name'] == self.selected_category:
                    cat['scale'] = self.current_scales
                    break
            logging.debug(f"Scale '{self.selected_scale}' description updated.")
            self.refresh()

class CategoryScaleWidget(Static):
    """Widget that combines CategoryWidget and ScaleWidget."""
    CSS_PATH = "category_widgets.css"
    def __init__(self, llm_call_manager, id=None):
        super().__init__(id=id)
        self.llm_call_manager = llm_call_manager
        self.all_categories = []
        self.category_widget = CategoryWidget(self.llm_call_manager, self.all_categories, id="category-widget")
        self.scale_widget = ScaleWidget(self.llm_call_manager, self.all_categories, id="scale-widget")

    def compose(self) -> ComposeResult:
        with Vertical(id="main-container"):
            yield self.category_widget
            yield self.scale_widget

    def on_category_selected(self, message: CategorySelected) -> None:
        """Handle CategorySelected messages from CategoryWidget."""
        self.scale_widget.update_scales(message.category_name)

class MainApp(App):
    CSS_PATH = "../mocks/category_widgets.css"

    def __init__(self):
        super().__init__()
        self.llm_call_manager = LLMCallManager()
        self.all_categories = []  # Initialize with an empty data structure
        logging.debug("MainApp initialized")

    def compose(self) -> ComposeResult:
        yield CategoryScaleWidget(self.llm_call_manager)
     
if __name__ == "__main__":
    logging.info("Starting MainApp")
    app = MainApp()
    app.run()

