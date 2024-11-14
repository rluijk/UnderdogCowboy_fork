import logging
import asyncio
import copy
            

from typing import Tuple, Optional, Dict, Any, List

from textual import on
from textual.reactive import Reactive
from textual.app import App, ComposeResult
from textual.containers import Vertical, Grid
from textual.widgets import Label, Select, Input, Static, TextArea, Button
from textual.message import Message

# LLM
from agent_llm_handler import (
                                send_agent_data_to_llm, run_category_call, 
                                run_scale_call, run_category_title_change, 
                                run_category_description_change
                                )

from llm_call_manager import LLMCallManager

# Events
from events.llm_events import LLMCallComplete, LLMCallError
from events.category_events import CategoryDataUpdate, CategorySelected

# UI related
from ui_components.session_dependent import SessionDependentUI
from ui_components.bound_text_area import BoundTextArea

# Events
from events.chat_events import TextSubmitted


class CategoryScaleWidget(SessionDependentUI):
    """
    Container widget that coordinates CategoryWidget and ScaleWidget.
    Responsibilities:
    - Combines category and scale widgets in a vertical layout
    - Manages shared category data structure
    - Coordinates communication between widgets
    """
  
    # Reactive Properties
    categories = Reactive[List[Dict]](default=[])
    selected_category = Reactive[Optional[str]](None)

    scales = Reactive([])
    # selected_scale = Reactive()

    def __init__(self, session_manager, screen_name, agent_name_plain: str, id: Optional[str] = None):
        """Initialize the coordinator widget."""
        super().__init__(session_manager, screen_name, agent_name_plain)
        self.agent_name = agent_name_plain
        self.session_manager = session_manager
        self.screen_name = screen_name
        self.load_category_data(self.agent_name)

    def _init_widgets(self) -> None:
        """Initialize child widgets with shared data reference."""
        self.category_widget = CategoryWidget(
            categories=self.categories,
            agent_name=self.agent_name,
            session_manager=self.session_manager,
            screen_name=self.screen_name
        )
        self.scale_widget = ScaleWidget(
            agent_name=self.agent_name,
            session_manager=self.session_manager,
            screen_name=self.screen_name
        )

    def compose(self) -> ComposeResult:
        self._init_widgets() # move directly into compose 

        """Layout child widgets vertically."""
        with Vertical(id="main-container"):
            yield self.category_widget
            yield self.scale_widget

    def load_category_data(self, agent_name: str):
        """Load category data from storage, including scales, and update the reactive variable."""
        
        # Fetch stored data for the specified agent
        agent_data = self.get_or_initialize_category_data(agent_name)
        
        # Extract 'name', 'description', and 'scales' (if present) for each category
        self.categories = [
            {
                "name": category.get("name", ""), 
                "description": category.get("description", ""),
                "scales": category.get("scales", [])  # Retain existing scales or default to an empty list
            }
            for category in agent_data.get("categories", [])
            if "name" in category and "description" in category
        ]



    def get_or_initialize_category_data(self, agent_name: str) -> dict:
            """Retrieve or initialize category data for an agent."""
            all_agents_data = self.session_manager.get_data("agents", screen_name=self.screen_name)
            if all_agents_data and agent_name in all_agents_data:
                return all_agents_data[agent_name]

            new_agent_data = {
                "categories": [],
                "meta_notes": "",
                "base_agent": agent_name
            }
            if all_agents_data:
                all_agents_data[agent_name] = new_agent_data
            else:
                all_agents_data = {agent_name: new_agent_data}

            # self.session_manager.update_data("agents", all_agents_data, self.screen_name)
            return new_agent_data   

    @on(CategoryDataUpdate)
    def handle_category_data_update(self, event: CategoryDataUpdate) -> None:
        """Handle an update event for category data and save updated data to storage."""
        self.update_category_data()

    def update_category_data(self) -> None:
        """Save the current state of the agent's data, including all categories and scales, into local storage."""
        
        # Step 1: Prepare updated categories with scales for the selected category
        updated_categories = []
        
        # Iterate through categories and add scales to the selected one
        for category in self.categories:
            # Copy category data
            updated_category = copy.deepcopy(category)
            # If this is the selected category, add scales
            if updated_category["name"] == self.selected_category:
                if len(self.scales) > 0:
                    updated_category["scales"] = self.scales  # Add the scales for the selected category
            
            updated_categories.append(updated_category)
        
        # Step 2: Construct the updated agent data
        updated_agent_data = {
            "categories": updated_categories,  # Use categories with updated scales for the selected category
            "meta_notes": "",
            "base_agent": self.agent_name
        }

        # Step 3: Retrieve the entire 'agents' data from storage and update for the current agent
        all_agents_data = self.session_manager.get_data("agents", screen_name=self.screen_name) or {}
        all_agents_data[self.agent_name] = updated_agent_data
        
        # Step 4: Persist updated data to storage
        self.session_manager.update_data("agents", all_agents_data, self.screen_name)


    def watch_selected_category(self, old_value: Optional[str], new_value: Optional[str]) -> None:
            """Propagate category selection to scale widget."""
            if new_value:
                self.scale_widget.selected_category = new_value

class CategoryWidget(SessionDependentUI):
    """
    Widget for managing categories.
    Responsibilities:
    - Manages category selection and updates
    - Coordinates with SelectCategoryWidget for UI
    - Handles category-related LLM operations
    """
    
    # Reactive Properties
    selected_category = Reactive[Optional[str]](None)
    is_loading = Reactive[bool](False)
    categories = Reactive[List[Dict]](default=[]) # new Reactive "wrapper" around our reference passed in.
    show_controls = Reactive[bool](False) 

    def __init__(self, categories, agent_name, session_manager, screen_name):
        super().__init__(session_manager, screen_name, agent_name)
        self.selected_category = None
        self._categories_reference = categories 
        self.agent_name = agent_name
        self.category_components = SelectCategoryWidget(agent_name, session_manager, categories)  # This contains the select widget

    def compose(self) -> ComposeResult:
        """Compose widget layout."""
        yield self.category_components

    def on_mount(self) -> None:
        """Initialize LLM manager after mount."""
        self.llm_call_manager = LLMCallManager()
        self.llm_call_manager.set_message_post_target(self)
        logging.info(f"Post target message set to: {self.llm_call_manager._message_post_target}")

        # Now assign the reference content to the reactive categories variable
        self.categories = self._categories_reference

    def update_select_options(self, options):
        self.category_components.select.set_options(options)

    # Reactive Watchers
    
    def watch_selected_category(self, old_value: Optional[str], new_value: Optional[str]) -> None:
        """React to category selection changes."""
        self.category_components.selected_category = new_value

        if new_value and new_value not in ["create_initial", "refresh_all"]:
            # Retrieve the category's description from self.categories
            category_data = next((cat for cat in self.categories if cat['name'] == new_value), None)
            category_description = category_data.get('description', '') if category_data else ''
            
            # shared state
            self.app.query_one(CategoryScaleWidget).selected_category = self.selected_category
            self.app.query_one(SelectScaleWidget).selected_category = self.selected_category
            
            # Directly update title and description in SelectCategoryWidget
            self.category_components.update_category_details(new_value, category_description)


    def watch_categories(self, old_value: list, new_value: list) -> None:
        """React to categories list changes."""
        try:
            # Ensure we're working with a list of dictionaries
            if isinstance(new_value, list):
                options = [("refresh_all", "Refresh All")] + [
                    (cat['name'], cat['name']) for cat in new_value 
                    if isinstance(cat, dict) and 'name' in cat
                ]
                # Access select through category_components
                self.category_components.select.set_options(options)
                self.refresh()
            else:
                logging.error(f"Invalid categories format: {type(new_value)}")
                self.notify("Invalid categories format received", severity="error")
        except Exception as e:
            logging.error(f"Error updating categories: {e}")
            self.notify(f"Error updating categories: {str(e)}", severity="error")


    def watch_is_loading(self, old_value: bool, new_value: bool) -> None:
        """React to loading state changes."""
        if hasattr(self.category_components, 'is_loading'):
            self.category_components.is_loading = new_value

    # Event Handlers
    @on(Select.Changed, "#category-select")
    async def handle_category_changed(self, event: Select.Changed) -> None:
        """Handle category selection changes."""
        selected_value = event.value
        
        # communication with other widget
        scale_select = self.app.query_one(SelectScaleWidget).scale_select

        scale_input_box = self.app.query_one(SelectScaleWidget).scale_input_box
        scale_description_area = self.app.query_one(SelectScaleWidget).scale_description_area

        # clear scales
        # self.app.query_one(CategoryScaleWidget).scales = []
        # self.app.query_one(SelectScaleWidget).scales = []


        logging.info(f"Category Select changed: {selected_value}")

        if selected_value == Select.BLANK:
            self.selected_category = None
            self.show_controls = False
            scale_select.set_options([])  # Clear scale options
            return

        if selected_value == "Create Initial Categories":
            self.show_controls = False  # Hide controls during creation
            await self._create_initial_categories()
            scale_select.set_options([])  # Clear scale options
            return

        # Find the selected category data
        category = next((cat for cat in self.categories if cat['name'] == selected_value), None)
       
        if category:
            self.selected_category = category['name']

            # Extract scales
            scales = category.get('scales', [])
            scale_options = [(scale['name'],scale['name'] ) for scale in scales]  # Adjust based on your scale structure

            # Update the scale_select widget
            scale_select.set_options(scale_options)

            logging.info(f"Scales updated for category '{selected_value}': {scale_options}")
        else:
            logging.warning(f"Selected category '{selected_value}' not found in data.")
            self.scale_select.set_options([])  # Clear scale options if category not found


    # LLM Event Handlers
    @on(LLMCallComplete)
    async def handle_llm_call_complete(self, event: LLMCallComplete) -> None:
        """Handle LLM call completions."""
        if event.input_id == "create-initial-categories":
            self.app.query_one(CategoryScaleWidget).categories = event.result['categories'] 
            self.app.query_one(SelectCategoryWidget).categories = event.result['categories']
            #self.categories = event.result['categories']

            await self._handle_initial_categories_complete(event)

    @on(LLMCallError)
    async def handle_llm_call_error(self, event: LLMCallError) -> None:
        """Handle LLM call errors."""
        self.is_loading = False
        
    # Private Methods
    async def _create_initial_categories(self) -> None:
        """Create initial categories using LLM."""
        self.is_loading = True
        self.show_controls = False
        try:
            config = self._get_llm_config()
            if not config:
                return

            # Update SelectCategoryWidget state
            self.category_components.show_edit_controls = False
            self.category_components.select.disabled = True  # Disable select during loading
         
            llm_config, current_agent = config
            pre_prompt = "prompt to get initial categories"
            session_name = self.session_manager.current_session_name.plain
            await self.llm_call_manager.submit_llm_call_with_agent(
                llm_function=run_category_call,
                llm_config=llm_config,
                session_name=session_name,
                agent_name=current_agent,
                agent_type="assessment",
                input_id="create-initial-categories",
                pre_prompt=pre_prompt,
                post_prompt=None
            )
        except Exception as e:
            #self.show_error(f"Failed to create categories: {str(e)}")
            logging.error(f"Error in create_initial_categories: {e}")
        finally:
            self.is_loading = False

    async def _refresh_all_categories(self) -> None:
        """Refresh all categories using LLM."""
        self.is_loading = True
        try:
            config = self._get_llm_config()
            if not config:
                return

            llm_config, current_agent = config
            pre_prompt = "prompt to refresh all"
            
            await self.llm_call_manager.submit_llm_call_with_agent(
                llm_function=send_agent_data_to_llm,
                llm_config=llm_config,
                agent_name=current_agent,
                agent_type="assessment",
                input_id="refresh-categories",
                pre_prompt=pre_prompt,
                post_prompt=None
            )
        except Exception as e:
            self.show_error(f"Failed to refresh categories: {str(e)}")
            logging.error(f"Error in refresh_categories: {e}")
        finally:
            self.is_loading = False

    async def _handle_initial_categories_complete(self, event: LLMCallComplete) -> None:
        """Handle completion of initial categories creation."""
        try:
            # Set initializing flag in SelectCategoryWidget
            self.app.query_one(SelectCategoryWidget).initializing = True

            if isinstance(event.result, dict) and 'categories' in event.result:
                categories = event.result['categories']
            else:
                categories = event.result

            # Update the reactive categories property
            self.categories = categories  # This will trigger watch_categories

            # If we have categories, set the selected category to the first one
            if categories:
                first_category = categories[0]
                title = first_category.get('name', '')
                description = first_category.get('description', '')

                # Set the selected category and update details
                self.selected_category = title  # Triggers watchers
                self.category_components.title_value = title
                self.category_components.description_area.value = description
                self.category_components.description_area.refresh()

            # Enable controls after successful load
            self.category_components.select.disabled = False
            self.show_controls = True

        except Exception as e:
            logging.error(f"Error processing create-initial-categories result: {e}")
            self.notify("Failed to create initial categories.", severity="error")
        finally:
            # Unset initializing flag in SelectCategoryWidget
            self.app.query_one(SelectCategoryWidget).initializing = False

    def _get_llm_config(self) -> Optional[Tuple[Dict[str, Any], str]]:
        """Get LLM configuration and agent."""
        llm_config = self.app.get_current_llm_config()
        if not llm_config:
            self.show_error("No LLM configuration available.")
            return None
        
        if not self.agent_name:
            self.show_error("No agent currently loaded.")
            return None

        return (llm_config, self.agent_name)

class SelectCategoryWidget(Static):
    """Widget for the UI components of categories."""
    
    
    # Reactive properties
    selected_category = Reactive[Optional[str]](None)
    is_loading = Reactive[bool](False)
    categories = Reactive[List[Dict]](default=[])
    show_controls = Reactive[bool](False)

    # Additional reactive properties 
    title_value = Reactive[str]("")  
    description_value = Reactive[str]("")  
    show_edit_controls = Reactive[bool](False)

    def __init__(self, agent_name, session_manager, categories):
        super().__init__()
        self.agent_name = agent_name
        self._categories_reference = categories
        self.session_manager = session_manager

    def compose(self) -> ComposeResult:
        """Compose widget layout, yielding each component."""
        # Define the widget layout here
        yield Select(
            options=[("create_initial", "Create Initial Categories")],
            id="category-select"
        )
        yield Static("Loading categories...", id="loading-indicator")
        yield Input(placeholder="Rename selected category", id="category-input")
        yield BoundTextArea("", id="category-description-area")
        with Grid(id="grid-buttons", classes="grid-buttons"):
            yield Button("Refresh Title", id="refresh-title-button", classes="action-button")
            yield Button("Refresh Description", id="refresh-description-button", classes="action-button")
        # yield Button("Refresh Both", id="refresh-both-button")
        yield Label("Modify Directly or use buttons for agent assistance", id="lbl_text")


    def on_mount(self) -> None:

        """Initialize states and hide elements after widgets are mounted."""
        self.select = self.query_one("#category-select", Select)
        self.loading_indicator = self.query_one("#loading-indicator", Static)
        self.input_box = self.query_one("#category-input", Input)
        self.description_area = self.query_one("#category-description-area", BoundTextArea)
        self.refresh_title_button = self.query_one("#refresh-title-button", Button)
        self.refresh_description_button = self.query_one("#refresh-description-button", Button)
        # self.refresh_both_button = self.query_one("#refresh-both-button", Button)
        self.lbl_text = self.query_one("#lbl_text", Label)

        # Initial visibility setup
        self.loading_indicator.visible = False
        self.input_box.visible = False
        self.description_area.visible = False
        self.refresh_title_button.visible = False
        self.refresh_description_button.visible = False
        # self.refresh_both_button.visible = False
        self.lbl_text.visible = False

        self.categories = self._categories_reference

        """Initialize components after mount."""
        self.llm_call_manager = LLMCallManager()
        self.llm_call_manager.set_message_post_target(self)
        logging.info(f"Post target message set to: {self.llm_call_manager._message_post_target}")


    def update_category_details(self, title: str, description: str) -> None:
        """Update both title and description for the selected category."""
        self.title_value = title
        self.description_value = description

    def update_options(self, options):
        """Helper method to update select options."""
        self.select.set_options(options)
        self.refresh()

    # Reactive watchers
    def watch_is_loading(self, old_value: bool, new_value: bool) -> None:
        """React to loading state changes."""
        if self.loading_indicator:
            self.loading_indicator.visible = new_value
            # Hide other controls during loading
            if new_value:
                self.show_edit_controls = False
            self.refresh()

    def watch_show_edit_controls(self, old_value: bool, new_value: bool) -> None:
        """React to edit controls visibility changes."""
        if not self.is_loading:  # Only show controls if not loading
            self.input_box.visible = new_value
            self.description_area.visible = new_value
            self.refresh_title_button.visible = new_value
            self.refresh_description_button.visible = new_value
            # self.refresh_both_button.visible = new_value
            self.lbl_text.visible = new_value
            
            # if self.selected_category is not None
            has_scales = any(
                item.get('scales') for item in self.categories if item.get('name') == self.selected_category and 'scales' in item
            )

            selected_scales_widget = self.app.query_one(SelectScaleWidget)
            if has_scales:
                # If scales exist, show the scale select dropdown in the other widget
                selected_scales_widget.create_scales_button.visible = False
                selected_scales_widget.scale_select.visible = True
                selected_scales_widget.scale_input_box.visible = False
                selected_scales_widget.scale_description_area.visible = False 
            else:
                # No scales present, show the "Create Initial Scales" button in the other widget
                selected_scales_widget.create_scales_button.visible = True
                selected_scales_widget.scale_select.visible = False
                selected_scales_widget.scale_input_box.visible = False
                selected_scales_widget.scale_description_area.visible = False

            # Refresh the external widget to apply visibility changes
            selected_scales_widget.refresh()
                    


    def watch_title_value(self, old_value: str, new_value: str) -> None:
        """React to title value changes."""
        # Skip updates if we're in the initialization phase
        if getattr(self, 'initializing', False):
            return

        # Update the name in `self.categories`
        for category in self.categories:
            if category.get("name") == self.selected_category:
                category["name"] = new_value
                break

        # Update the select box options and check that it includes the new value
        updated_options = [
            (category.get("name"), category.get("name"))
            for category in self.categories
        ]
        
        # Log the updated options to ensure they are set correctly
        logging.debug(f"Updated select options: {updated_options}")

        self.select.set_options(updated_options)
        
        # Verify that new_value exists in updated options before setting it
        option_values = [option[1] for option in updated_options]
        if new_value in option_values:
            self.select.value = new_value  # Set the select to reflect the selected value
        else:
            logging.warning(f"Value '{new_value}' not found in options; available options: {option_values}")
        
        # Update the input box and refresh it
        self.input_box.value = new_value
        self.input_box.refresh()

        # Notify that the category data has been updated
        self.post_message(CategoryDataUpdate())


    def watch_description_value(self, old_value: str, new_value: str) -> None:
        """React to description value changes and update the current category's description."""
        # Locate the selected category within `self.categories` and update its description
        for category in self.categories:
            if category.get("name") == self.selected_category:
                category["description"] = new_value
                break
        
        # Update the TextArea to reflect the new description
        self.description_area.load_text(new_value)
        self.description_area.refresh()
        
        # Refresh categories to ensure the reactive system registers the change
        self.categories = self.categories  # Trigger update by assigning the modified list to itself
        self.post_message(CategoryDataUpdate())

    def watch_categories(self, new_value: List[Dict], old_value: List[Dict]) -> None:
        """Watch changes to categories and update options in select."""
        options = [("refresh_all", "Refresh All")] + [(cat['name'], cat['name']) for cat in new_value]
        self.select.set_options(options)  # Access to `select` is safe here
        self.refresh()        

    def watch_selected_category(self, old_value: Optional[str], new_value: Optional[str]) -> None:
        """React to category selection changes."""
        if not new_value or new_value in ["create_initial", "refresh_all"]:
            self.show_edit_controls = False
            return

        # Set controls to be visible
        self.show_edit_controls = True
        
        # Update title
        self.title_value = new_value
      
    # LLM Configuration
    def _llm_config_current_agent(self) -> Optional[Tuple[Dict[str, Any], str]]:
        """Get LLM configuration and current agent."""
        llm_config = self.app.get_current_llm_config()
        if not llm_config:
            self.show_error("No LLM configuration available.")
            return None
        
        if not self.agent_name:
            self.show_error("No agent currently loaded.")
            return None

        return (llm_config, self.agent_name)

    # Async operations
    async def refresh_title(self) -> None:
        """Refresh title using LLM."""
        self.is_loading = True
        try:
            config = self._llm_config_current_agent()
            if not config:
                return
            
            llm_config, current_agent = config
            session_name = self.session_manager.current_session_name.plain
          
            await self.llm_call_manager.submit_llm_call_with_agent_with_id_and_sesssion(
                llm_function=run_category_title_change,
                llm_config=llm_config,
                agent_name=current_agent,
                agent_type="assessment",
                category_to_change=self.selected_category,
                session_name=session_name,
                input_id="category-input"
            )
        except Exception as e:
            logging.error(f"Error in refresh_title: {e}")
        finally:
            self.is_loading = False


    async def refresh_description(self) -> None:
        """Refresh description using LLM."""
        self.is_loading = True
        try:
            config = self._llm_config_current_agent()
            if not config:
                return
                                
            llm_config, current_agent = config
            session_name = self.session_manager.current_session_name.plain
            
            await self.llm_call_manager.submit_llm_call_with_agent_with_id_and_sesssion(
                llm_function=run_category_description_change,
                llm_config=llm_config,
                agent_name=current_agent,
                agent_type="assessment",
                category_to_change=self.selected_category,
                session_name=session_name,
                input_id="category-description-area"
            )
        except Exception as e:
            logging.error(f"Error in refresh_description: {e}")
        finally:
            self.is_loading = False

    async def refresh_both(self) -> None:
        """Refresh both title and description concurrently."""
        self.is_loading = True
        try:
            config = self._llm_config_current_agent()
            if not config:
                return
            
            llm_config, current_agent = config
            await asyncio.gather(
                self.refresh_title(),
                self.refresh_description()
            )
        finally:
            self.is_loading = False

    # Event handlers
    @on(CategorySelected)
    def handle_category_selected(self, message: CategorySelected) -> None:
        """Handle the CategorySelected message to set title and description."""
        self.title_value = message.category_name  # Update the title value
        self.input_box.value = self.title_value  # Set the input box with the title
        self.input_box.refresh()

        self.description_value = message.category_description  # Update the description value
        self.description_area.value = self.description_value  # Set the TextArea with the description
        self.description_area.refresh()   

    @on(LLMCallComplete)
    async def handle_llm_call_complete(self, event: LLMCallComplete) -> None:
        """Handle LLM call completions."""
        handlers = {
            "category-input": self._handle_title_update,
            "category-description-area": self._handle_description_update,
            "refresh-categories": self._handle_categories_update,
            "retrieve-scales": self._handle_scales_update
        }
        
        handler = handlers.get(event.input_id)
        if handler:
            try:
                await handler(event.result)
            except Exception as e:
                logging.error(f"Error processing {event.input_id}: {e}")
                self.show_error(f"Failed to process {event.input_id}")

    @on(LLMCallError)
    async def handle_llm_call_error(self, event: LLMCallError) -> None:
        """Handle LLM call errors."""
        logging.error(f"LLM call error for {event.input_id}: {event.error}")
        # self.show_error(event.error)
        self.is_loading = False

    @on(Button.Pressed)
    async def handle_button_press(self, event: Button.Pressed) -> None:
        """Handle button press events."""
        handlers = {
            "refresh-title-button": self.refresh_title,
            "refresh-description-button": self.refresh_description,
            "refresh-both-button": self.refresh_both
        }
        
        handler = handlers.get(event.button.id)
        if handler:
            await handler()

    # Event Handlers for Input and TextArea changes
    @on(Input.Submitted, "#category-input")
    def handle_title_input_changed(self, event: Input.Submitted) -> None:
        """Update title_value from the input box when the user types."""
        self.title_value = event.value # Sync the reactive variable with the input

    @on(TextSubmitted)
    async def handle_text_submission(self, event: TextSubmitted):
        self.description_value = event.text # Sync the reactive variable with the textarea
    
    # LLM result handlers
    async def _handle_title_update(self, result: dict) -> None:
        """Handle title update from LLM result."""
        self.title_value = result

    async def _handle_description_update(self, result: dict) -> None:
        """Handle description update from LLM result."""
        self.description_value = result

    async def _handle_categories_update(self, result: dict) -> None:
        """Handle categories update from LLM result."""
        self.categories = result
        # If there's a selected category, update its details
        if self.selected_category:
            category_data = next(
                (cat for cat in result if cat['name'] == self.selected_category),
                None
            )
            if category_data:
                self.title_value = category_data['name']
                self.description_value = category_data.get('description', '')

    async def _handle_scales_update(self, result: dict) -> None:
        """Handle scales update from LLM result."""
        if self.selected_category:
            for cat in self.categories:
                if cat['name'] == self.selected_category:
                    cat['scales'] = result
                    break

class ScaleWidget(SessionDependentUI):
    """Widget for managing scales within a selected category."""
    
    # Reactive properties
    selected_category = Reactive(None)
    selected_scale = Reactive(None)
    scales = Reactive([])
    is_loading = Reactive(False)
    show_scales = Reactive(False)

    def __init__(self, agent_name, session_manager, screen_name):
        super().__init__(session_manager, screen_name, agent_name)

        self.selected_category = self.app.query_one(CategoryScaleWidget).selected_category
        # we reference them as all_categories (we are working just with the selected category)
        self.all_categories = self.app.query_one(CategoryScaleWidget).categories
        self.session_manager = session_manager

        self.agent_name = agent_name
        self.scale_components = SelectScaleWidget()

    def compose(self) -> ComposeResult:
        yield self.scale_components

    def on_mount(self) -> None:
        """Initialize components after mount."""
        self.llm_call_manager = LLMCallManager()
        self.llm_call_manager.set_message_post_target(self)
        logging.info(f"Post target message set to: {self.llm_call_manager._message_post_target}")

    # Watchers
    def watch_selected_category(self, old_value: Optional[str], new_value: Optional[str]) -> None:
        """React to category selection changes."""
        if new_value:
            asyncio.create_task(self._update_scales_for_category(new_value))

    def watch_scales(self, old_value: List, new_value: List) -> None:
        """React to changes in current scales."""
        self.scale_components.scales = new_value
        self.show_scales = bool(new_value)

    def watch_is_loading(self, old_value: bool, new_value: bool) -> None:
        """React to loading state changes."""
        self.scale_components.is_loading = new_value

    def watch_selected_scale(self, old_value: Optional[str], new_value: Optional[str]) -> None:
        """React to scale selection changes."""
        self.scale_components.selected_scale = new_value
        if new_value:
            self._update_scale_details(new_value)

    # Private helper methods
    async def _update_scales_for_category(self, category_name: str) -> None:
        """Update scales for the selected category."""
        category_data = next(
            (cat for cat in self.all_categories if cat['name'] == category_name),
            None
        )
        if category_data:
            self.scales = category_data.get("scales", [])
            if not self.scales:
                # Show create button if no scales available
                # self.scale_components.show_create_button = True
                self.app.query_one(SelectScaleWidget).show_create_button = True
            else:
                # self.scale_components.show_create_button = False
                self.app.query_one(SelectScaleWidget).show_create_button = False
            logging.debug(f"Updated scales for category '{category_name}': {self.scales}")

    def _update_scale_details(self, scale_name: str) -> None:
        """Update the display of scale details."""
        scale_data = next(
            (scale for scale in self.scales if scale['name'] == scale_name),
            None
        )
        if scale_data:
            self.scale_components.title_value = scale_data.get('name', '')
            self.scale_components.description_value = scale_data.get('description', '')

    def _llm_config_current_agent(self) -> Optional[Tuple[Dict[str, Any], str]]:
        """Get LLM configuration and current agent."""
        llm_config = self.app.get_current_llm_config()
        if not llm_config:
            self.show_error("No LLM configuration available.")
            return None
        
        if not self.agent_name:
            self.show_error("No agent currently loaded.")
            return None

        return (llm_config, self.agent_name)

    # Async LLM operations
    async def retrieve_scales(self) -> None:
        """Retrieve scales using LLM."""
        self.is_loading = True
        try:
            config = self._llm_config_current_agent()
            if not config:
                return

            llm_config, current_agent = config
            session_name = self.session_manager.current_session_name.plain
            
            await self.llm_call_manager.submit_llm_call_with_agent_with_id_and_sesssion(
                llm_function=run_scale_call,
                llm_config=llm_config,
                agent_name=current_agent,
                agent_type="assessment",
                category_to_change=self.selected_category,
                session_name = session_name,
                input_id="retrieve-scales",
            )
        except Exception as e:
            logging.error(f"Error in retrieve_scales: {e}")
            self.show_error(str(e))
        finally:
            self.is_loading = False

    # Event handlers
    @on(Button.Pressed, "#create-scales-button")
    async def handle_create_scales(self, event: Button.Pressed) -> None:
        """Handle create scales button press."""
        logging.info(f"Creating initial scales for category '{self.selected_category}'")
        await self.retrieve_scales()

    @on(Select.Changed, "#scale-select")
    async def handle_scale_changed(self, event: Select.Changed) -> None:
        """Handle scale selection changes."""
        if event.value != Select.BLANK:
            self.selected_scale = event.value

    @on(Input.Submitted, "#scale-input")
    async def handle_scale_rename(self, event: Input.Submitted) -> None:
        """Handle scale rename submission."""
        if not self.selected_scale or not self.selected_category:
            return

        new_name = event.value.strip()
        if not new_name:
            logging.warning("Attempted to rename scale to an empty string.")
            return

        logging.info(f"Renaming scale '{self.selected_scale}' to '{new_name}'")
        self._update_scale_name(self.selected_scale, new_name)
        self.selected_scale = new_name

    @on(TextArea.Changed, "#scale-description-area")
    async def handle_description_change(self, event: TextArea.Changed) -> None:
        """Handle scale description changes."""
        if not self.selected_scale or not self.selected_category:
            return

        new_description = event.text_area.document.text.strip()
        self._update_scale_description(self.selected_scale, new_description)

    # LLM event handlers
    @on(LLMCallComplete)
    async def handle_llm_call_complete(self, event: LLMCallComplete) -> None:
        """Handle LLM call completions."""
        if event.input_id == "retrieve-scales":
            await self._handle_scales_update(event.result)

    @on(LLMCallError)
    async def handle_llm_call_error(self, event: LLMCallError) -> None:
        """Handle LLM call errors."""
        logging.error(f"LLM call error for {event.input_id}: {event.error}")
        self.show_error(event.error)
        self.is_loading = False

    async def _handle_scales_update(self, scales: List[Dict]) -> None:
        """Handle scales update from LLM result."""
        try:
            # Update the scales in all_categories
            for cat in self.all_categories:
                if cat['name'] == self.selected_category:
                    cat['scales'] = scales  # Corrected key
                    break
            
            # Update current scales (triggers watcher)
            self.scales = scales

            # Sync reactive state
            self.app.query_one(CategoryScaleWidget).scales = scales 
            
            logging.debug(f"Scales updated for category '{self.selected_category}': {scales}")
            logging.info("sending post for CategoryDataUpdate after scales are in")
            self.post_message(CategoryDataUpdate())
            


        except Exception as e:
            logging.error(f"Error updating scales: {e}")

    def _update_scale_name(self, old_name: str, new_name: str) -> None:
        """Update scale name in data structures."""
        updated_scales = self.scales.copy()
        for scale in updated_scales:
            if scale['name'] == old_name:
                scale['name'] = new_name
                break
        self.scales = updated_scales  # Trigger watcher

        # Update in all_categories
        for cat in self.all_categories:
            if cat['name'] == self.selected_category:
                cat['scales'] = updated_scales
                break

    def _update_scale_description(self, scale_name: str, new_description: str) -> None:
        """Update scale description in data structures."""
        updated_scales = self.scales.copy()
        for scale in updated_scales:
            if scale['name'] == scale_name:
                scale['description'] = new_description
                break
        self.scales = updated_scales  # Trigger watcher

        # Update in all_categories
        for cat in self.all_categories:
            if cat['name'] == self.selected_category:
                cat['scales'] = updated_scales
                break

class SelectScaleWidget(Static):
    """Widget for the UI components of scales."""
    
    # Reactive properties
    selected_category = Reactive[Optional[str]](None) 
    selected_scale = Reactive(None)
    is_loading = Reactive(False)
    show_edit_controls = Reactive(False)
    scales = Reactive([])
    title_value = Reactive("")
    description_value = Reactive("")
    show_create_button = Reactive(False)

    def __init__(self):
        super().__init__()

    def _init_widgets(self):
        """Initialize all widget components."""
        self.create_scales_button = Button("Create Initial Scales", id="create-scales-button", classes="action-button").add_class("hidden")
        self.scale_select = Select([], id="scale-select").add_class("hidden")
        self.loading_indicator = Static("Loading scales...", id="scale-loading-indicator")
        self.scale_input_box = Input(placeholder="Rename selected scale", id="scale-input").add_class("hidden")
        self.scale_description_area = BoundTextArea("", id="scale-description-area").add_class("hidden")

    def compose(self) -> ComposeResult:
        self._init_widgets() # TODO untangle this pattern 

        yield self.create_scales_button
        yield self.scale_select
        yield self.loading_indicator
        yield self.scale_input_box
        yield self.scale_description_area

    # Watchers
    def watch_selected_category(self, old_value: bool, new_value: bool) -> None:
        if new_value:
            self.app.notify(f"selected category {new_value}")
            self.scale_select.remove_class("hidden")
        else:
            self.app.notify(f"selected category {new_value}")    

    def watch_is_loading(self, old_value: bool, new_value: bool) -> None:
        """React to loading state changes."""
        self.loading_indicator.visible = new_value
        self.refresh()

    def watch_show_edit_controls(self, old_value: bool, new_value: bool) -> None:
        """React to edit controls visibility changes."""
        self.scale_input_box.visible = new_value
        self.scale_description_area.visible = new_value

        self.scale_input_box.remove_class("hidden")
        self.scale_description.remove_class("hidden")

        self.refresh()

    def watch_scales(self, old_value: list, new_value: list) -> None:
        """React to scales list changes."""
        options = [("create_initial", "Create Initial Scales")] if self.show_create_button else []
        options += [(scale['name'], scale['name']) for scale in new_value]
        self.scale_select.set_options(options)
        self.scale_select.visible = bool(new_value) or self.show_create_button
        self.refresh()

    def watch_show_create_button(self, old_value: bool, new_value: bool) -> None:
        """React to create button visibility changes."""
        self.create_scales_button.visible = new_value
        self.refresh()

    def watch_title_value(self, old_value: str, new_value: str) -> None:
        """React to title value changes."""
        if new_value != self.scale_input_box.value:
            self.scale_input_box.value = new_value
            self.scale_input_box.refresh()

    def watch_description_value(self, old_value: str, new_value: str) -> None:
        """React to description value changes."""
        if new_value != self.scale_description_area.text:
            self.scale_description_area.load_text(new_value) 
            self.scale_description_area.refresh()

    def watch_selected_scale(self, old_value: Optional[str], new_value: Optional[str]) -> None:
        """React to scale selection changes."""
        if not new_value or new_value == "create_initial":
            # No scale selected or 'create_initial' selected, hide edit controls
            self.show_edit_controls = False
            self.scale_input_box.visible = False
            self.scale_description_area.visible = False
            return

        # A valid scale is selected, show the edit controls
        self.show_edit_controls = True
        self.scale_input_box.visible = True
        self.scale_description_area.visible = True

        # Find the selected scale data and update the input fields
        scale_data = next(
            (scale for scale in self.scales if scale['name'] == new_value),
            None
        )
        if scale_data:
            self.title_value = scale_data.get('name', '')
            self.description_value = scale_data.get('description', '')
            self.scale_input_box.value = self.title_value
            self.scale_description_area.load_text(self.description_value)
            logging.debug(f"Selected scale '{new_value}' with data: {scale_data}")

        # Refresh to ensure changes are visible
        self.refresh()
            