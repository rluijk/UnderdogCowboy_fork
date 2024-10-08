import logging
import asyncio
from concurrent.futures import ThreadPoolExecutor
from textual import on
from textual.app import App, ComposeResult
from textual.containers import Vertical, Container, Horizontal
from textual.widgets import Header, Select, Input, Static, TextArea, Button
from textual.message import Message

# Configure the main logger to log to 'app.log'
logging.basicConfig(
    filename='app_inspiration.log',
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

    def simulate_refresh_both(self, current_title, current_description):
        """Simulate refreshing both title and description."""
        import time
        logging.debug("Simulating refresh for both title and description...")
        time.sleep(2)  # Simulate processing delay
        return f"{current_title} (Refreshed)", f"{current_description} (Refreshed)"

    def simulate_refresh_title(self, current_title):
        """Simulate refreshing the title."""
        import time
        logging.debug("Simulating refresh for title...")
        time.sleep(2)  # Simulate processing delay
        return f"{current_title} (Title Refreshed)"

    def simulate_refresh_description(self, current_description):
        """Simulate refreshing the description."""
        import time
        logging.debug("Simulating refresh for description...")
        time.sleep(2)  # Simulate processing delay
        return f"{current_description} (Description Refreshed)"

class CategorySelected(Message):
    """Custom message to indicate a category has been selected."""
    def __init__(self, sender, category_name: str):
        super().__init__()
        self.sender = sender
        self.category_name = category_name

class EditableField(Vertical):
    """Widget that combines an Input, a TextArea, and three Buttons aligned horizontally."""
    
    def __init__(self, llm_call_manager, placeholder="", id=None):
        super().__init__(id=id)
        self.llm_call_manager = llm_call_manager
        self.placeholder = placeholder

        # Flag to prevent infinite loop
        self.updating = False

        # Configure a separate logger for EditableField
        self.logger = logging.getLogger(f"EditableField.{self.id}")
        self.logger.setLevel(logging.DEBUG)

        # Create file handler for inspiration.log
        fh = logging.FileHandler('inspiration.log')
        fh.setLevel(logging.DEBUG)

        # Create formatter and add it to the handler
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        fh.setFormatter(formatter)

        # Add handler to the logger if not already added
        if not self.logger.handlers:
            self.logger.addHandler(fh)

    def compose(self):
        self.logger.debug("Composing EditableField widgets.")

        # Create the Input widget
        self.input_box = Input(placeholder=self.placeholder, id=f"{self.id}-input")
        self.logger.debug("Created Input widget.")
        yield self.input_box

        # Create the TextArea widget
        self.text_area = TextArea("", id=f"{self.id}-textarea")
        self.logger.debug("Created TextArea widget.")
        yield self.text_area

        # Create a Horizontal container for buttons
        with Horizontal(id=f"{self.id}-button-container", classes="button-container"):
            # Create Buttons
            self.refresh_both_button = Button("Refresh Both", id=f"{self.id}-refresh-both")
            self.logger.debug("Created 'Refresh Both' Button.")
            yield self.refresh_both_button

            self.refresh_title_button = Button("Refresh Title", id=f"{self.id}-refresh-title")
            self.logger.debug("Created 'Refresh Title' Button.")
            yield self.refresh_title_button

            self.refresh_description_button = Button("Refresh Description", id=f"{self.id}-refresh-description")
            self.logger.debug("Created 'Refresh Description' Button.")
            yield self.refresh_description_button

    @on(Button.Pressed)
    async def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id
        self.logger.info(f"Button pressed: {button_id}")

        if button_id.endswith("-refresh-both"):
            self.logger.debug("Initiating refresh_both.")
            await self.refresh_both()
        elif button_id.endswith("-refresh-title"):
            self.logger.debug("Initiating refresh_title.")
            await self.refresh_title()
        elif button_id.endswith("-refresh-description"):
            self.logger.debug("Initiating refresh_description.")
            await self.refresh_description()

    async def refresh_both(self):
        """Refresh both title and description."""
        current_title = self.input_box.value
        current_description = self.text_area.value
        self.logger.info("Refreshing both title and description...")

        try:
            new_title, new_description = await self.llm_call_manager.run_llm_call(
                self.llm_call_manager.simulate_refresh_both,
                current_title,
                current_description
            )
            self.logger.debug(f"Received new title: {new_title}")
            self.logger.debug(f"Received new description: {new_description}")

            self.updating = True
            self.input_box.value = new_title
            self.text_area.value = new_description
            self.updating = False

            self.logger.info("Both title and description refreshed successfully.")
            self.refresh()
        except Exception as e:
            self.logger.error(f"Error refreshing both title and description: {e}")

    async def refresh_title(self):
        """Refresh only the title."""
        current_title = self.input_box.value
        self.logger.info("Refreshing title...")

        try:
            new_title = await self.llm_call_manager.run_llm_call(
                self.llm_call_manager.simulate_refresh_title,
                current_title
            )
            self.logger.debug(f"Received new title: {new_title}")

            self.updating = True
            self.input_box.value = new_title
            self.updating = False

            self.logger.info("Title refreshed successfully.")
            self.refresh()
        except Exception as e:
            self.logger.error(f"Error refreshing title: {e}")

    async def refresh_description(self):
        """Refresh only the description."""
        current_description = self.text_area.value
        self.logger.info("Refreshing description...")

        try:
            new_description = await self.llm_call_manager.run_llm_call(
                self.llm_call_manager.simulate_refresh_description,
                current_description
            )
            self.logger.debug(f"Received new description: {new_description}")

            self.updating = True
            self.text_area.value = new_description
            self.updating = False

            self.logger.info("Description refreshed successfully.")
            self.refresh()
        except Exception as e:
            self.logger.error(f"Error refreshing description: {e}")

    @on(Input.Submitted)
    def on_input_submitted(self, event: Input.Submitted) -> None:
        if self.updating:
            self.logger.debug("Ignoring Input.Submitted event during update.")
            return
        self.logger.debug("Input.Submitted event received.")
        # Forward the event
        self.post_message(event)

    @on(TextArea.Changed)
    def on_text_area_changed(self, event: TextArea.Changed) -> None:
        if self.updating:
            self.logger.debug("Ignoring TextArea.Changed event during update.")
            return
        self.logger.debug("TextArea.Changed event received.")
        # Forward the event
        self.post_message(event)

    def set_title(self, title: str):
        """Set the title in the Input widget."""
        self.logger.debug(f"Setting title to: {title}")
        self.updating = True
        self.input_box.value = title
        self.input_box.refresh()
        self.updating = False
        self.logger.debug("Title set and refreshed.")

    def set_description(self, description: str):
        """Set the description in the TextArea widget."""
        self.logger.debug(f"Setting description to: {description}")
        self.updating = True
        self.text_area.value = description
        self.text_area.refresh()
        self.updating = False
        self.logger.debug("Description set and refreshed.")

class CategoryWidget(Static):
    """Widget for managing categories."""
    def __init__(self, llm_call_manager, all_categories, id=None):
        super().__init__(id=id)
        self.llm_call_manager = llm_call_manager
        self.all_categories = all_categories  # Datastructure passed via init
        self.categories = [("create_initial", "Create Initial Categories")]
        self.selected_category = None

    def compose(self) -> ComposeResult:
        # Category select widget
        self.select = Select(self.categories, id="category-select")
        yield self.select

        # Loading indicator for categories
        self.loading_indicator = Static("  Loading categories...", id="loading-indicator")
        self.loading_indicator.visible = False
        yield self.loading_indicator

        # EditableField for category name and description
        self.editable_field = EditableField(
            llm_call_manager=self.llm_call_manager,
            placeholder="Rename selected category",
            id="category-editable-field"
        )
        self.editable_field.visible = False
        yield self.editable_field

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
            await self.show_loading_indicator()
            # Asynchronously retrieve categories via LLMCallManager
            asyncio.create_task(self.retrieve_categories())

        elif selected_value == "Refresh All":
            # Show loading indicator and simulate async retrieval of new categories
            self.select.set_options([("waiting", "Refreshing categories...")])
            await self.show_loading_indicator()
            # Asynchronously retrieve new categories via LLMCallManager
            asyncio.create_task(self.retrieve_new_categories())

        else:
            # Handle category selection
            self.selected_category = selected_value
            self.editable_field.visible = True
            self.editable_field.set_title(selected_value)

            # Find the description of the selected category
            selected_category_data = next(
                (cat for cat in self.all_categories if cat['name'] == selected_value), None
            )
            if selected_category_data:
                self.editable_field.set_description(selected_category_data["description"])
                logging.info(f"Category selected: {selected_value}, description displayed.")

                # Post the message (will be handled by MainApp)
                self.post_message(CategorySelected(self, self.selected_category))
            else:
                logging.error(f"Selected category '{selected_value}' not found.")
                self.editable_field.set_description("Category not found.")

            self.refresh()

    async def show_loading_indicator(self):
        """Show the loading indicator."""
        self.loading_indicator.visible = True
        self.refresh()

    async def hide_loading_indicator(self):
        """Hide the loading indicator."""
        self.loading_indicator.visible = False
        self.refresh()

    async def retrieve_categories(self):
        """Retrieve categories via LLMCallManager."""
        try:
            categories = await self.llm_call_manager.run_llm_call(self.llm_call_manager.simulate_category_retrieval)
            self.all_categories[:] = categories  # Update the passed-in datastructure
            self.categories = [("refresh_all", "Refresh All")] + [(cat['name'], cat['name']) for cat in categories]
            self.select.set_options(self.categories)
            self.select.value = categories[0]['name']  # Automatically select the first category
            logging.debug(f"Categories retrieved: {categories}")
        except Exception as e:
            logging.error(f"Error retrieving categories: {e}")
            self.select.set_options([("error", "Error loading categories")])
        finally:
            await self.hide_loading_indicator()
            self.refresh()

    async def retrieve_new_categories(self):
        """Retrieve new categories via LLMCallManager for Refresh All."""
        try:
            new_categories = await self.llm_call_manager.run_llm_call(self.llm_call_manager.simulate_new_categories)
            self.all_categories[:] = new_categories  # Update the passed-in datastructure
            self.categories = [("refresh_all", "Refresh All")] + [(cat['name'], cat['name']) for cat in self.all_categories]
            self.select.set_options(self.categories)
            self.select.value = new_categories[0]['name']  # Automatically select the first new category
            logging.debug(f"New categories retrieved: {new_categories}")
        except Exception as e:
            logging.error(f"Error retrieving new categories: {e}")
            self.select.set_options([("error", "Error loading new categories")])
        finally:
            await self.hide_loading_indicator()
            self.refresh()

    @on(Input.Submitted, "#category-editable-field-input")
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
            self.editable_field.visible = False
            logging.debug(f"Category renamed to '{new_name}'")
            self.refresh()

    @on(TextArea.Changed, "#category-editable-field-textarea")
    def category_description_changed(self, event: TextArea.Changed) -> None:
        # Handle category description updates
        if self.selected_category:
            new_description = event.text.strip()
            logging.info(f"Updating description for category '{self.selected_category}'")
            for cat in self.all_categories:
                if cat['name'] == self.selected_category:
                    cat['description'] = new_description
                    break
            logging.debug(f"Category '{self.selected_category}' description updated.")
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

    def compose(self) -> ComposeResult:
        # Create scales button
        self.create_scales_button = Button("Create Initial Scales", id="create-scales-button")
        self.create_scales_button.visible = False
        yield self.create_scales_button

        # Scale select widget
        self.scale_select = Select([], id="scale-select")
        self.scale_select.visible = False
        yield self.scale_select

        # Loading indicator for scales
        self.loading_indicator = Static("  Loading scales...", id="scale-loading-indicator")
        self.loading_indicator.visible = False
        yield self.loading_indicator

        # EditableField for scale name and description
        self.editable_field = EditableField(
            llm_call_manager=self.llm_call_manager,
            placeholder="Rename selected scale",
            id="scale-editable-field"
        )
        self.editable_field.visible = False
        yield self.editable_field

    def update_scales(self, selected_category_name):
        """Update scales based on the selected category."""
        self.selected_category = selected_category_name
        # Find the selected category in all_categories
        selected_category_data = next(
            (cat for cat in self.all_categories if cat['name'] == selected_category_name), None
        )
        if selected_category_data:
            self.current_scales = selected_category_data.get("scale", [])
            if self.current_scales:
                # Populate the scale select widget
                self.scale_select.set_options([(scale['name'], scale['name']) for scale in self.current_scales])
                self.scale_select.value = self.current_scales[0]['name']
                self.scale_select.visible = True
                self.editable_field.visible = True
                self.create_scales_button.visible = False
                # Display the first scale's details
                self.editable_field.set_title(self.current_scales[0]['name'])
                self.editable_field.set_description(self.current_scales[0]['description'])
                self.logger.debug(f"Scale '{self.current_scales[0]['name']}' details displayed.")
            else:
                # No scales available
                self.scale_select.set_options([])
                self.scale_select.visible = False
                self.editable_field.visible = False
                self.create_scales_button.visible = True  # Show the button to create scales
        else:
            # Category not found
            self.current_scales = []
            self.scale_select.set_options([])
            self.scale_select.visible = False
            self.editable_field.visible = False
            self.create_scales_button.visible = False
        self.refresh()

    @on(Button.Pressed, "#create-scales-button")
    async def create_scales_pressed(self, event: Button.Pressed) -> None:
        logging.info(f"Creating initial scales for category '{self.selected_category}'")
        # Show loading indicator and start async retrieval of scales
        self.create_scales_button.visible = False
        self.loading_indicator.visible = True
        self.refresh()
        # Asynchronously retrieve scales via LLMCallManager
        asyncio.create_task(self.retrieve_scales())

    async def retrieve_scales(self):
        """Retrieve scales via LLMCallManager for the selected category."""
        try:
            scales = await self.llm_call_manager.run_llm_call(
                self.llm_call_manager.simulate_scale_retrieval,
                self.selected_category
            )
            # Update the scales in the selected category
            for cat in self.all_categories:
                if cat['name'] == self.selected_category:
                    cat['scale'] = scales
                    break
            self.current_scales = scales
            # Populate the scale select widget
            self.scale_select.set_options([(scale['name'], scale['name']) for scale in scales])
            self.scale_select.value = scales[0]['name']
            self.scale_select.visible = True
            self.editable_field.visible = True
            self.create_scales_button.visible = False
            logging.debug(f"Scales retrieved for category '{self.selected_category}': {scales}")
            # Display the first scale's details
            self.editable_field.set_title(scales[0]['name'])
            self.editable_field.set_description(scales[0]['description'])
        except Exception as e:
            logging.error(f"Error retrieving scales for category '{self.selected_category}': {e}")
        finally:
            self.loading_indicator.visible = False
            self.refresh()

    def display_scale_details(self, scale_name):
        """Display details of the selected scale."""
        self.selected_scale = scale_name
        selected_scale_data = next(
            (scale for scale in self.current_scales if scale['name'] == scale_name), None
        )
        if selected_scale_data:
            self.editable_field.visible = True
            self.editable_field.set_title(selected_scale_data['name'])
            self.editable_field.set_description(selected_scale_data['description'])
            logging.debug(f"Scale '{selected_scale_data['name']}' details displayed.")
        else:
            self.editable_field.visible = False
        self.refresh()

    @on(Select.Changed, "#scale-select")
    async def scale_changed(self, event: Select.Changed) -> None:
        selected_scale = event.value
        logging.info(f"Scale Select changed: {selected_scale}")
        if selected_scale == Select.BLANK:
            logging.info("No scale selection made (BLANK)")
            return
        self.display_scale_details(selected_scale)

    @on(Input.Submitted, "#scale-editable-field-input")
    def scale_input_submitted(self, event: Input.Submitted) -> None:
        # Handle scale renaming
        if self.selected_scale and self.selected_category:
            new_name = event.value.strip()
            if not new_name:
                logging.warning("Attempted to rename scale to an empty string.")
                return
            logging.info(f"Renaming scale '{self.selected_scale}' to '{new_name}' in category '{self.selected_category}'")
            # Update the scale in current_scales
            for scale in self.current_scales:
                if scale['name'] == self.selected_scale:
                    scale['name'] = new_name
                    break
            # Update the scales in the selected category
            for cat in self.all_categories:
                if cat['name'] == self.selected_category:
                    cat['scale'] = self.current_scales
                    break
            # Update the scale select options
            self.scale_select.set_options([(scale['name'], scale['name']) for scale in self.current_scales])
            self.scale_select.value = new_name
            self.selected_scale = new_name
            logging.debug(f"Scale renamed to '{new_name}'")
            self.refresh()

    @on(TextArea.Changed, "#scale-editable-field-textarea")
    def scale_description_changed(self, event: TextArea.Changed) -> None:
        # Handle scale description updates
        if self.selected_scale and self.selected_category:
            new_description = event.text.strip()
            logging.info(f"Updating description for scale '{self.selected_scale}' in category '{self.selected_category}'")
            # Update the scale's description
            for scale in self.current_scales:
                if scale['name'] == self.selected_scale:
                    scale['description'] = new_description
                    break
            # Update the scales in the selected category
            for cat in self.all_categories:
                if cat['name'] == self.selected_category:
                    cat['scale'] = self.current_scales
                    break
            logging.debug(f"Scale '{self.selected_scale}' description updated.")
            self.refresh()

class MainApp(App):
    
    CSS_PATH = "category_widgets_02.css"
    
    def __init__(self):
        super().__init__()
        self.llm_call_manager = LLMCallManager()
        self.all_categories = []  # Initialize with an empty data structure
        logging.debug("MainApp initialized")

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(id="main-container"):
            with Container(id="category-container"):
                self.category_widget = CategoryWidget(
                    llm_call_manager=self.llm_call_manager,
                    all_categories=self.all_categories,
                    id="category-widget"
                )
                yield self.category_widget

            with Container(id="scale-container"):
                self.scale_widget = ScaleWidget(
                    llm_call_manager=self.llm_call_manager,
                    all_categories=self.all_categories,
                    id="scale-widget"
                )
                yield self.scale_widget

    @on(CategorySelected)
    def on_category_selected(self, message: CategorySelected) -> None:
        """Handle CategorySelected messages from CategoryWidget."""
        logging.debug(f"MainApp received CategorySelected message: {message.category_name}")
        self.scale_widget.update_scales(message.category_name)

    async def on_mount(self) -> None:
        # Optionally, perform any setup when the app is mounted
        pass

if __name__ == "__main__":
    logging.info("Starting MainApp")
    app = MainApp()
    app.run()
    logging.info("MainApp has terminated")
