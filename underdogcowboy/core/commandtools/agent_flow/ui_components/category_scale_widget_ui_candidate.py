import logging
import asyncio
import copy
            

from typing import Tuple, Optional, Dict, Any, List

from textual import on
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
from events.category_events import CategoryDataUpdate, CategorySelected, ScalesUpdated

# UI related
from ui_components.session_dependent import SessionDependentUI
from ui_components.bound_text_area import BoundTextArea

# Events
from events.chat_events import TextSubmitted

from typing import Optional, List, Dict
from textual.message import Message

class SharedState(SessionDependentUI):
    """A shared state class to manage state across multiple widgets."""
    def __init__(self):
        self._selected_category: Optional[str] = None
        self._categories: List[Dict] = []
        self._scales: List[Dict] = []

    @property
    def selected_category(self) -> Optional[str]:
        return self._selected_category

    @selected_category.setter
    def selected_category(self, value: Optional[str]) -> None:
        self._selected_category = value
        # Emit an event when the selected category changes
        self.app.post_message(CategorySelected(category_name=value))
        
    @property
    def categories(self) -> List[Dict]:
        return self._categories

    @categories.setter
    def categories(self, value: List[Dict]) -> None:
        self._categories = value
        # Emit an event when the categories list changes
        self.app.post_message(CategoryDataUpdate())

    @property
    def scales(self) -> List[Dict]:
        return self._scales

    @scales.setter
    def scales(self, value: List[Dict]) -> None:
        self._scales = value
        # Emit an event when the scales list changes
        self.app.message_post_target.post_message(ScalesUpdated())

class CategoryScaleWidget(SessionDependentUI):
  

    def __init__(self, session_manager, screen_name, agent_name_plain: str, id: Optional[str] = None):
        """Initialize the coordinator widget."""
        super().__init__(session_manager, screen_name, agent_name_plain)
        
        # ui related state
        self.shared_state = SharedState()

        self.agent_name = agent_name_plain
        self.session_manager = session_manager
        self.screen_name = screen_name
        self.load_category_data(self.agent_name)

    def _init_widgets(self) -> None:

        """Initialize child widgets with shared data reference."""
        self.category_widget = CategoryWidget(
            shared_state = self.shared_state,
            agent_name=self.agent_name,
            session_manager=self.session_manager,
            screen_name=self.screen_name
        )
        self.scale_widget = ScaleWidget(
            shared_state = self.shared_state,
            agent_name=self.agent_name,
            session_manager=self.session_manager,
            screen_name=self.screen_name
        )

         # Add widgets to the app
        self.mount(self.category_widget)
        self.mount(self.scale_widget)

        # Ensure the widgets are mounted before querying
        self.call_later(self._populate_select_box)


    def _populate_select_box(self) -> None:
        """Populate the select box if categories are available."""
        if self.shared_state.categories:
            options = [(cat['name'], cat['name']) for cat in self.shared_state.categories]
            
            # Query the select box by its ID after all widgets are mounted
            select_widget = self.app.query_one("#category-select")
            select_widget.set_options(options)
    

    def compose(self) -> ComposeResult:
        self._init_widgets() # move directly into compose 

        """Layout child widgets vertically."""
        with Vertical(id="main-container"):
            yield self.category_widget
            yield self.scale_widget

    def load_category_data(self, agent_name: str) -> None:
        """Load category data from storage, update shared state, and populate the select box."""
        
        # Fetch stored data for the specified agent
        agent_data = self.get_or_initialize_category_data(agent_name)

        # Extract 'name', 'description', and 'scales' (if present) for each category
        categories = [
            {
                "name": category.get("name", ""), 
                "description": category.get("description", ""),
                "scales": category.get("scales", [])
            }
            for category in agent_data.get("categories", [])
            if "name" in category and "description" in category
        ]

        # Update shared state with the loaded categories
        self.shared_state.categories = categories


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
        
        # Step 1: Prepare updated categories using the shared state
        updated_categories = []

        # Iterate through categories from the shared state and update scales if necessary
        for category in self.shared_state.categories:
            updated_category = copy.deepcopy(category)
            
            # If this is the selected category, update scales
            if updated_category["name"] == self.shared_state.selected_category:
                if len(self.shared_state.scales) > 0:
                    updated_category["scales"] = self.shared_state.scales
            
            updated_categories.append(updated_category)
        
        # Step 2: Construct the updated agent data using the shared state
        updated_agent_data = {
            "categories": updated_categories,
            "meta_notes": "",  # Placeholder for additional data if needed
            "base_agent": self.agent_name
        }

        # Step 3: Retrieve the current agents' data from storage
        all_agents_data = self.session_manager.get_data("agents", screen_name=self.screen_name) or {}
        
        # Step 4: Update the agent's data with the current state and persist it
        all_agents_data[self.agent_name] = updated_agent_data
        self.session_manager.update_data("agents", all_agents_data, self.screen_name)

        # Log success for debugging
        logging.info(f"Agent data updated and saved for {self.agent_name}.")


class CategoryWidget(SessionDependentUI):
    
    def __init__(self, shared_state, agent_name, session_manager, screen_name):
        super().__init__(session_manager, screen_name, agent_name)
        
        # ui related state
        self.shared_state = shared_state

        self.selected_category = None
        self.agent_name = agent_name
        self.category_components = SelectCategoryWidget(agent_name, session_manager, shared_state)  # This contains the select widget

    def compose(self) -> ComposeResult:
        """Compose widget layout."""
        yield self.category_components

    def on_mount(self) -> None:
        """Initialize LLM manager after mount."""
        self.llm_call_manager = LLMCallManager()
        self.llm_call_manager.set_message_post_target(self)
        logging.info(f"Post target message set to: {self.llm_call_manager._message_post_target}")

    def update_select_options(self, options):
        self.category_components.select.set_options(options)

   # Event Handlers
    @on(Select.Changed, "#category-select")
    async def handle_category_changed(self, event: Select.Changed) -> None:
        """Handle category selection changes and notify other widgets."""
        selected_value = event.value
        logging.info(f"Category Select changed: {selected_value}")

        if selected_value == Select.BLANK:
            self.shared_state.selected_category = None
            self.show_controls = False
            # Emit event to clear scales in other widgets
            self.post_message(CategorySelected(category_name=None))
            return

        if selected_value == "Create Initial Categories":
            self.show_controls = False
            await self._create_initial_categories()
            # Emit event to notify other widgets about scale clearing
            # self.post_message(CategorySelected(category_name=None))
            return

        # Find the selected category data
        category = next((cat for cat in self.shared_state.categories if cat['name'] == selected_value), None)

        if category:
            self.shared_state.selected_category = category['name']

            # Emit the event to notify other components about the selected category
            self.post_message(CategorySelected(category_name=category['name']))

            logging.info(f"Category '{selected_value}' selected with scales: {category.get('scales', [])}")
        else:
            logging.warning(f"Selected category '{selected_value}' not found in data.")
            self.post_message(CategorySelected(category_name=None))


    # LLM Event Handlers
    @on(LLMCallComplete)
    async def handle_llm_call_complete(self, event: LLMCallComplete) -> None:
        """Handle LLM call completions."""
        if event.input_id == "create-initial-categories":
            # self.app.query_one(CategoryScaleWidget).categories = event.result['categories'] 
            # self.app.query_one(SelectCategoryWidget).categories = event.result['categories']
            # self.categories = event.result['categories']

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
        """Handle completion of initial categories creation and populate select options."""
        try:
            categories = event.result.get('categories', event.result) if isinstance(event.result, dict) else event.result
            
            # Extract category names to populate the select box
            if categories:

                # Update shared state with the retrieved categories
                self.shared_state.categories = categories    

                options = [(cat.get('name', ''), cat.get('name', '')) for cat in categories]
                self.category_components.select.set_options(options)

                # Set the first category as selected and update details
                first_category = categories[0]
                self.category_components.title_value = first_category.get('name', '')
                self.category_components.description_area.value = first_category.get('description', '')
                self.category_components.description_area.refresh()

            self.category_components.select.disabled = False
            self.show_controls = True

        except Exception as e:
            logging.error(f"Error processing create-initial-categories result: {e}")
            self.notify("Failed to create initial categories.", severity="error")


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
    
    
    def __init__(self, agent_name, session_manager, shared_state):
        super().__init__()
        self.agent_name = agent_name
        self.shared_state = shared_state
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
                category_to_change=self.shared_state.selected_category,
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
                category_to_change=self.shared_state.selected_category,
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

    @on(Select.Changed, "#category-select")
    def handle_select(self, event: Select.Changed) -> None:
        """Handle category selection changes."""
        if event.value and event.value not in (Select.BLANK, "Create Initial Categories"):
            # Update the selected category in shared state
            self.shared_state.selected_category = event.value
            logging.info(f"Category '{event.value}' selected.")

            # Fetch category details from shared state storage
            category_data = next(
                (cat for cat in self.shared_state.categories if cat['name'] == event.value), 
                None
            )

            # Populate the input box and description area with stored values
            if category_data:
                self.input_box.value = category_data.get('name', '')
                self.description_area.load_text(category_data.get('description', '')) 
                self.refresh_title_button.visible = True
                self.refresh_description_button.visible= True
            else:
                self.input_box.value = ""
                self.description_area.load_text("")
                self.refresh_title_button.visible = False
                self.refresh_description_button.visible = False

            # Make input fields visible
            self.input_box.visible = True
            self.description_area.visible = True

        else:
            # Reset if invalid selection
            self.shared_state.selected_category = None
            self.input_box.visible = False
            self.description_area.visible = False
            logging.info("No valid category selected.")

        


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

    @on(Input.Submitted, "#category-input")
    def handle_title_input_changed(self, event: Input.Submitted) -> None:
        """Handle title input changes, update shared state, save to storage, and refresh select box."""
        if self.shared_state.selected_category:
            # Update the category name in the shared state
            for category in self.shared_state.categories:
                if category['name'] == self.shared_state.selected_category:
                    category['name'] = event.value
                    break

            # Update the input field with the new value
            self.title_value = event.value

            # Access the CategoryScaleWidget and update storage
            category_widget = self.app.query_one(CategoryScaleWidget)
            category_widget.update_category_data()

            # Refresh the select box options
            self._refresh_select_box()

            # Update the selected category to the new name
            select_widget = self.app.query_one("#category-select")
            # Ensure the updated name is in the options before setting it as selected
            if event.value in [option[0] for option in select_widget._options]:
                select_widget.value = event.value
            else:
                logging.warning(f"Updated category '{event.value}' not found in select options.")


    def _refresh_select_box(self) -> None:
        """Refresh the select box with updated categories from shared state."""
        select_widget = self.app.query_one("#category-select")
        
        # Populate the select box with updated category names
        options = [(cat['name'], cat['name']) for cat in self.shared_state.categories]
        select_widget.set_options(options)



    @on(TextSubmitted)
    async def handle_text_submission(self, event: TextSubmitted) -> None:
        """Handle description changes, update shared state, and save to storage."""
        # Update the shared state with the new description value
        if self.shared_state.selected_category:
            for category in self.shared_state.categories:
                if category['name'] == self.shared_state.selected_category:
                    category['description'] = event.text
                    break

            # Update the description field and persist changes
            self.description_value = event.text
            category_widget = self.app.query_one(CategoryScaleWidget)
            category_widget.update_category_data()


    def _update_storage(self) -> None:
        """Persist the updated shared state to storage."""
        updated_data = {
            "categories": self.shared_state.categories,
            "meta_notes": "",
            "base_agent": self.agent_name
        }
        all_agents_data = self.session_manager.get_data("agents", screen_name=self.screen_name) or {}
        all_agents_data[self.agent_name] = updated_data
        self.session_manager.update_data("agents", all_agents_data, self.screen_name)


    # LLM result handlers
    async def _handle_title_update(self, result: dict) -> None:
        """Handle title update from LLM result, update shared state, save to storage, and refresh the select box."""
        if self.shared_state.selected_category:
            # Update the shared state with the new title from LLM result
            for category in self.shared_state.categories:
                if category['name'] == self.shared_state.selected_category:
                    category['name'] = result
                    break

            # Update the title value in the input field
            self.title_value = result

            # Access the CategoryScaleWidget and persist changes
            category_widget = self.app.query_one(CategoryScaleWidget)
            category_widget.update_category_data()

            # Refresh the select box with updated categories
            self._refresh_select_box()

            # Update the select box to reflect the new title
            select_widget = self.app.query_one("#category-select")
            if result in [option[0] for option in select_widget._options]:
                select_widget.value = result
                
    async def _handle_description_update(self, result: dict) -> None:
        """Handle description update from LLM result, update shared state, and save to storage."""
        if self.shared_state.selected_category:
            # Update the shared state with the new description from LLM result
            for category in self.shared_state.categories:
                if category['name'] == self.shared_state.selected_category:
                    category['description'] = result
                    break

            # Update the description value in the text area
            description_area = self.app.query_one("#category-description-area")
            description_area.load_text(result) 

            # Access the CategoryScaleWidget and persist changes
            category_widget = self.app.query_one(CategoryScaleWidget)
            category_widget.update_category_data()

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

    def __init__(self, shared_state, agent_name, session_manager, screen_name):
        super().__init__(session_manager, screen_name, agent_name)
        self.shared_state = shared_state
        self.agent_name = agent_name
        self.scale_components = SelectScaleWidget(shared_state)
        self.scales = []
        self.selected_scale = None

    def compose(self) -> ComposeResult:
        """Compose the widget layout."""
        yield self.scale_components

    def on_mount(self) -> None:
        """Initialize components after mount."""
        self.llm_call_manager = LLMCallManager()
        self.llm_call_manager.set_message_post_target(self)
        logging.info(f"Post target message set for ScaleWidget.")
        
        # Initial UI state setup
        self._clear_scales()

    @on(CategorySelected)
    async def handle_category_selected(self, event: CategorySelected) -> None:
        """Handle category selection to display scales."""
        selected_category = event.category_name
        self.selected_scale = None

        # Clear previous state
        self._clear_scales()

        if selected_category:
            # Retrieve scales from shared state
            category_data = next(
                (cat for cat in self.shared_state.categories if cat['name'] == selected_category),
                None
            )

            if category_data and category_data.get('scales'):
                self.scales = category_data['scales']
                self._show_scales()
            else:
                self._show_create_scales_button()

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
                category_to_change=self.shared_state.selected_category,
                session_name=session_name,
                input_id="retrieve-scales"
            )
        except Exception as e:
            logging.error(f"Error in retrieve_scales: {e}")
        finally:
            self.is_loading = False

    @on(LLMCallComplete)
    async def handle_llm_call_complete(self, event: LLMCallComplete) -> None:
        """Handle LLM call completions."""
        if event.input_id == "retrieve-scales":
            await self._handle_scales_update(event.result)

    @on(LLMCallError)
    async def handle_llm_call_error(self, event: LLMCallError) -> None:
        """Handle LLM call errors."""
        logging.error(f"LLM call error: {event.error}")
        self.is_loading = False

    async def _handle_scales_update(self, scales: List[Dict]) -> None:
        """Update the shared state and UI with the retrieved scales."""
        if self.shared_state.selected_category:
            # Update the shared state
            for category in self.shared_state.categories:
                if category['name'] == self.shared_state.selected_category:
                    category['scales'] = scales
                    break
            self.scales = scales

            # Update UI
            self._show_scales()
            self.update_category_data()
            logging.info(f"Scales updated for category '{self.shared_state.selected_category}'.")

    def _clear_scales(self) -> None:
        """Clear scales and reset the UI."""
        self.scale_components.scale_select.set_options([])
        self.scale_components.scale_select.visible = False  # Ensure select box is hidden
        self.scale_components.create_scales_button.visible = False
        self.scale_components.scale_input_box.visible = False
        self.scale_components.scale_description_area.visible = False

    def _show_scales(self) -> None:
        """Display the scales in the select box if a category is selected."""
        if self.shared_state.selected_category and self.scales:
            scale_options = [(scale['name'], scale['name']) for scale in self.scales]
            self.scale_components.scale_select.set_options(scale_options)
            self.scale_components.scale_select.visible = True
            self.scale_components.create_scales_button.visible = False
        else:
            # If no category is selected or no scales exist, hide the select box
            self.scale_components.scale_select.visible = False
            
    def _show_create_scales_button(self) -> None:
        """Show the button to create initial scales if none exist."""
        self.scale_components.create_scales_button.visible = True
        self.scale_components.scale_select.visible = False

    def _llm_config_current_agent(self) -> Optional[Tuple[Dict[str, Any], str]]:
        """Get the LLM configuration."""
        llm_config = self.app.get_current_llm_config()
        if not llm_config:
            self.show_error("No LLM configuration available.")
            return None
        
        if not self.agent_name:
            self.show_error("No agent currently loaded.")
            return None

        return (llm_config, self.agent_name)


class SelectScaleWidget(Static):
    """Widget for the UI components of scales."""

    def __init__(self, shared_state):
        super().__init__()
        self.shared_state = shared_state

    def _init_widgets(self):
        """Initialize all widget components."""
        self.create_scales_button = Button("Create Initial Scales", id="create-scales-button", classes="action-button")
        self.scale_select = Select([], id="scale-select")
        self.scale_input_box = Input(placeholder="Rename selected scale", id="scale-input")
        self.scale_description_area = TextArea("", id="scale-description-area")

    def compose(self) -> ComposeResult:
        self._init_widgets()
        yield self.create_scales_button
        yield self.scale_select
        yield self.scale_input_box
        yield self.scale_description_area

    @on(Button.Pressed, "#create-scales-button")
    async def handle_create_scales_button(self, event: Button.Pressed) -> None:
        """Handle button press to create initial scales."""
        await self.parent.retrieve_scales()

    @on(Select.Changed, "#scale-select")
    def handle_scale_changed(self, event: Select.Changed) -> None:
        """Handle scale selection changes."""
        if event.value:
            scale_data = next(
                (scale for scale in self.parent.scales if scale['name'] == event.value),
                None
            )
            if scale_data:
                self.scale_input_box.value = scale_data.get('name', '')
                self.scale_description_area.value = scale_data.get('description', '')
                self.scale_input_box.visible = True
                self.scale_description_area.visible = True

class __bck__ScaleWidget(SessionDependentUI):
    """Widget for managing scales within a selected category."""
    
    def __init__(self, shared_state, agent_name, session_manager, screen_name):
        super().__init__(session_manager, screen_name, agent_name)

        self.session_manager = session_manager
        self.shared_state = shared_state
        self.agent_name = agent_name
        self.scale_components = SelectScaleWidget(shared_state)

    def compose(self) -> ComposeResult:
        yield self.scale_components

    def on_mount(self) -> None:
        """Initialize components after mount."""
        self.llm_call_manager = LLMCallManager()
        self.llm_call_manager.set_message_post_target(self)
        logging.info(f"Post target message set to: {self.llm_call_manager._message_post_target}")

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
    @on(CategorySelected)
    async def handle_category_selected(self, event: CategorySelected) -> None:
        """Update scales when a new category is selected."""
        selected_category = event.category_name

        if not selected_category:
            # Clear the scales if no category is selected
            self.scales = []
            self.scale_select.set_options([])
            return

        # Find the scales for the selected category
        category_data = next(
            (cat for cat in self.shared_state.categories if cat['name'] == selected_category),
            None
        )
        if category_data:
            self.scales = category_data.get('scales', [])
            scale_options = [(scale['name'], scale['name']) for scale in self.scales]
            self.scale_select.set_options(scale_options)
            logging.info(f"Scales updated for category '{selected_category}': {scale_options}")
        else:
            self.scale_select.set_options([])

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

class __bck__SelectScaleWidget(Static):
    
    def __init__(self,shared_state):
        super().__init__()
        self.shared_state = shared_state

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

  
            