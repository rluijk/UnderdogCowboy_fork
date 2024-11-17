import logging

from typing import List, Dict, Optional, Tuple, Any


from textual import on
from textual.reactive import Reactive
from textual.app import App, ComposeResult
from textual.containers import Vertical, Horizontal
from textual.widgets import Label, Header, Select, Input, Static, TextArea, Button
from textual.message import Message

import asyncio
from concurrent.futures import ThreadPoolExecutor

from textual.containers import Vertical, Horizontal
from textual.widgets import Label, Header, Select, Input, Static, TextArea, Button
from textual.message import Message

# UI related
from ui_components.session_dependent import SessionDependentUI

# LLM
from agent_llm_handler import send_agent_data_to_llm, run_category_call 
from llm_call_manager import LLMCallManager

# Events
from events.llm_events import LLMCallComplete, LLMCallError


class CategorySelected(Message):
    """Custom message to indicate a category has been selected."""
    
    def __init__(self, category_name: str, category_description: str = ""):
        super().__init__()
        self.category_name: str = category_name
        self.category_description: str = category_description

class CategoryScaleWidget(SessionDependentUI):
    """
    Container widget that coordinates CategoryWidget and ScaleWidget.
    Responsibilities:
    - Combines category and scale widgets in a vertical layout
    - Manages shared category data structure
    - Coordinates communication between widgets
    """
  
    # Reactive Properties
    categories: Reactive[List[Dict]] = Reactive([])
    selected_category: Reactive[Optional[str]] = Reactive(None)

    def __init__(self, session_manager, screen_name, agent_name_plain: str, id: Optional[str] = None):
        """Initialize the coordinator widget."""
        super().__init__(session_manager, screen_name, agent_name_plain)
        self.agent_name = agent_name_plain
        self.session_manager = session_manager
        self.screen_name = screen_name
        self._init_widgets()
        self.executor = ThreadPoolExecutor(max_workers=5)  # For synchronous storage methods

    def _init_widgets(self) -> None:
        """Initialize child widgets with shared data reference."""
        self.category_widget = CategoryWidget(
            all_categories=self.categories,
            agent_name=self.agent_name,
            #id="category-widget",
            session_manager=self.session_manager,
            screen_name=self.screen_name
        )
        self.scale_widget = ScaleWidget(
            all_categories=self.categories,
            agent_name=self.agent_name,
            #id="scale-widget",
            session_manager=self.session_manager,
            screen_name=self.screen_name
        )

    def compose(self) -> ComposeResult:
        """Layout child widgets vertically."""
        with Vertical(id="main-container"):
            yield self.category_widget
            yield self.scale_widget

    def watch_selected_category(self, old_value: Optional[str], new_value: Optional[str]) -> None:
        """Propagate category selection to scale widget."""
        if new_value:
            self.scale_widget.selected_category = new_value

    def watch_categories(self, old_categories: List[Dict], new_categories: List[Dict]) -> None:
        """Watcher that updates storage whenever categories change."""
        asyncio.create_task(self.update_storage_async(new_categories))
    
    async def on_mount(self) -> None:
        """Load or initialize category data when the widget mounts."""
        # Retrieve or initialize category data
        category_data = await self.get_or_initialize_category_data_async(self.agent_name)
        
        # Set the reactive property
        self.categories = category_data.get("categories", [])

    async def get_or_initialize_category_data_async(self, agent_name: str) -> dict:
        """Asynchronous method to retrieve or initialize category data for an agent."""
        # Run synchronous get_data in executor
        all_agents_data = await asyncio.get_event_loop().run_in_executor(
            self.executor,
            self.session_manager.get_data,
            "agents",
            self.screen_name
        )
        
        if all_agents_data and agent_name in all_agents_data:
            return all_agents_data[agent_name]

        # Initialize new agent data
        new_agent_data = {
            "categories": [],
            "meta_notes": "",
            "base_agent": agent_name
        }

        if all_agents_data:
            all_agents_data[agent_name] = new_agent_data
        else:
            all_agents_data = {agent_name: new_agent_data}

        # Run synchronous update_data in executor
        await asyncio.get_event_loop().run_in_executor(
            self.executor,
            self.session_manager.update_data,
            "agents",
            all_agents_data,
            self.screen_name
        )
        
        return new_agent_data

    async def update_storage_async(self, categories: List[Dict]) -> None:
        """Asynchronously update the storage with the new categories."""
        # Run synchronous get_data in executor
        all_agents_data = await asyncio.get_event_loop().run_in_executor(
            self.executor,
            self.session_manager.get_data,
            "agents",
            self.screen_name
        )
        
        if not all_agents_data:
            all_agents_data = {}
        
        # Update the specific agent's categories
        if self.agent_name in all_agents_data:
            all_agents_data[self.agent_name]["categories"] = categories
        else:
            all_agents_data[self.agent_name] = {
                "categories": categories,
                "meta_notes": "",
                "base_agent": self.agent_name
            }
        
        # Run synchronous update_data in executor
        await asyncio.get_event_loop().run_in_executor(
            self.executor,
            self.session_manager.update_data,
            "agents",
            all_agents_data,
            self.screen_name
        )

class CategoryWidget(SessionDependentUI):


    """
    Widget for managing categories.
    Responsibilities:
    - Manages category selection and updates
    - Coordinates with SelectCategoryWidget for UI
    - Handles category-related LLM operations
    """
    
    # Reactive Properties
    selected_category: Reactive[Optional[str]] = Reactive(None)
    is_loading: Reactive[bool] = Reactive(False)
    categories: Reactive[List[Dict]] = Reactive(default=[])
    show_controls: Reactive[bool] = Reactive(False) 

    def __init__(self, all_categories: Reactive[List[Dict]], agent_name: str, session_manager, screen_name: str, id: Optional[str] = None):
        super().__init__(session_manager, screen_name, agent_name)
        self.selected_category = None
        self.categories = all_categories  # Reference to shared reactive property
        self.agent_name = agent_name
        self.category_components = SelectCategoryWidget(all_categories, 
                                                        agent_name, session_manager, screen_name, 
                                                        id = None)  
        
    def compose(self) -> ComposeResult:
        """Compose widget layout."""
        yield self.category_components

    async def on_mount(self) -> None:
        """Initialize LLM manager after mount."""
        self.llm_call_manager = LLMCallManager()
        self.llm_call_manager.set_message_post_target(self)
        logging.info(f"Post target message set to: {self.llm_call_manager._message_post_target}")

    def update_select_options(self, options: List[Tuple[str, str]]) -> None:
        """Update the select widget options."""
        self.category_components.select.set_options(options)

    # Reactive Watchers
    
    def watch_selected_category(self, old_value: Optional[str], new_value: Optional[str]) -> None:
        """React to category selection changes."""
        self.category_components.selected_category = new_value

        if new_value and new_value not in ["create_initial", "refresh_all"]:
            # Retrieve the category's description from self.categories
            category_data = next((cat for cat in self.categories if cat['name'] == new_value), None)
            category_description = category_data.get('description', '') if category_data else ''

            # Directly update title and description in SelectCategoryWidget
            self.category_components.update_category_details(new_value, category_description)

    def watch_categories(self, old_value: List[Dict], new_value: List[Dict]) -> None:
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
                self.show_error("Invalid categories format received")
        except Exception as e:
            logging.error(f"Error updating categories: {e}")
            self.show_error(f"Error updating categories: {str(e)}")

    def watch_is_loading(self, old_value: bool, new_value: bool) -> None:
        """React to loading state changes."""
        if hasattr(self.category_components, 'is_loading'):
            self.category_components.is_loading = new_value

    # Event Handlers
    @on(Select.Changed, "#category-select")
    async def handle_category_changed(self, event: Select.Changed) -> None:
        """Handle category selection changes."""
        selected_value = event.value
        logging.info(f"Category Select changed: {selected_value}")

        if selected_value == "":  # Assuming Select.BLANK is represented by an empty string
            self.selected_category = None
            self.show_controls = False
            return

        if selected_value == "Create Initial Categories":
            self.show_controls = False  # Hide controls during creation
            await self._create_initial_categories()
            return

        self.selected_category = selected_value
        self.show_controls = True 

    # LLM Event Handlers
    @on(LLMCallComplete)
    async def handle_llm_call_complete(self, event: LLMCallComplete) -> None:
        """Handle LLM call completions."""
        if event.input_id == "create-initial-categories":
            await self._handle_initial_categories_complete(event)
        elif event.input_id == "refresh-categories":
            await self._handle_refresh_categories_complete(event)

    @on(LLMCallError)
    async def handle_llm_call_error(self, event: LLMCallError) -> None:
        """Handle LLM call errors."""
        self.is_loading = False
        self.show_error(f"LLM operation failed: {event.error}")

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
            
            await self.llm_call_manager.submit_llm_call_with_agent(
                llm_function=run_category_call,
                llm_config=llm_config,
                agent_name=current_agent,
                agent_type="assessment",
                input_id="create-initial-categories",
                pre_prompt=pre_prompt,
                post_prompt=None
            )
        except Exception as e:
            self.show_error(f"Failed to create categories: {str(e)}")
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
            if isinstance(event.result, dict) and 'categories' in event.result:
                categories = event.result['categories']
            else:
                categories = event.result
                
            self.categories = categories  # Update shared reactive property
            
            # If we have categories, update both title and description for the first one
            if categories:
                first_category = categories[0]
                self.category_components.title_value = first_category.get('name', '')
                self.category_components.description_area.value = first_category.get('description', '')
                self.category_components.description_area.refresh()
            
            # Enable controls after successful load
            self.category_components.select.disabled = False
            self.show_controls = True
        except Exception as e:
            logging.error(f"Error processing create-initial-categories result: {e}")
            self.show_error("Failed to create initial categories.")

    async def _handle_refresh_categories_complete(self, event: LLMCallComplete) -> None:
        """Handle completion of categories refresh."""
        try:
            if isinstance(event.result, dict) and 'categories' in event.result:
                categories = event.result['categories']
            else:
                categories = event.result

            self.categories = categories  # Update shared reactive property

            # Optionally, update UI components based on refreshed categories
            if categories:
                # For example, select the first category
                self.selected_category = categories[0].get('name')
                self.category_components.title_value = categories[0].get('name', '')
                self.category_components.description_area.value = categories[0].get('description', '')
                self.category_components.description_area.refresh()

            self.show_controls = True
        except Exception as e:
            logging.error(f"Error processing refresh-categories result: {e}")
            self.show_error("Failed to refresh categories.")

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

    def show_error(self, message: str) -> None:
        """Display an error message to the user."""
        self.notify(message, severity="error")
        logging.error(message)

class ScaleWidget(SessionDependentUI):
    """Widget for managing scales within a selected category."""
    
    # Reactive properties
    selected_category: Reactive[Optional[str]] = Reactive(None)
    selected_scale: Reactive[Optional[str]] = Reactive(None)
    current_scales: Reactive[List[Dict]] = Reactive(default=[])
    is_loading: Reactive[bool] = Reactive(False)
    show_scales: Reactive[bool] = Reactive(False)

    def __init__(
        self,
        all_categories: Reactive[List[Dict]],
        agent_name: str,
        session_manager,
        screen_name: str,
        id: Optional[str] = None
    ):
        """Initialize the ScaleWidget."""
        super().__init__(session_manager, screen_name, agent_name)
        self.all_categories = all_categories  # Reference to shared categories
        self.agent_name = agent_name
        self.scale_components = SelectScaleWidget()

    def compose(self) -> ComposeResult:
        """Compose widget layout."""
        yield self.scale_components

    async def on_mount(self) -> None:
        """Initialize LLM manager after mount."""
        self.llm_call_manager = LLMCallManager()
        self.llm_call_manager.set_message_post_target(self)
        logging.info(f"Post target message set to: {self.llm_call_manager._message_post_target}")

    # Reactive Watchers
    def watch_selected_category(
        self,
        old_value: Optional[str],
        new_value: Optional[str]
    ) -> None:
        """React to category selection changes."""
        if new_value:
            asyncio.create_task(self._update_scales_for_category(new_value))

    def watch_current_scales(
        self,
        old_value: List[Dict],
        new_value: List[Dict]
    ) -> None:
        """React to changes in current scales."""
        self.scale_components.scales = new_value
        self.show_scales = bool(new_value)

    def watch_is_loading(
        self,
        old_value: bool,
        new_value: bool
    ) -> None:
        """React to loading state changes."""
        self.scale_components.is_loading = new_value

    def watch_selected_scale(
        self,
        old_value: Optional[str],
        new_value: Optional[str]
    ) -> None:
        """React to scale selection changes."""
        self.scale_components.selected_scale = new_value
        if new_value:
            self._update_scale_details(new_value)

    # Private helper methods
    async def _update_scales_for_category(
        self,
        category_name: str
    ) -> None:
        """Update scales for the selected category."""
        category_data = next(
            (cat for cat in self.all_categories if cat['name'] == category_name),
            None
        )
        if category_data:
            self.current_scales = category_data.get("scale", [])
            if not self.current_scales:
                # Show create button if no scales available
                self.scale_components.show_create_button = True
            else:
                self.scale_components.show_create_button = False

    def _update_scale_details(self, scale_name: str) -> None:
        """Update the display of scale details."""
        scale_data = next(
            (scale for scale in self.current_scales if scale['name'] == scale_name),
            None
        )
        if scale_data:
            self.scale_components.title_value = scale_data.get('name', '')
            self.scale_components.description_value = scale_data.get('description', '')
            self.scale_components.description_area.refresh()

    def _llm_config_current_agent(
        self
    ) -> Optional[Tuple[Dict[str, Any], str]]:
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
            pre_prompt = f"Please provide scales for the category: {self.selected_category}"
            
            await self.llm_call_manager.submit_llm_call_with_agent(
                llm_function=send_agent_data_to_llm,
                llm_config=llm_config,
                agent_name=current_agent,
                agent_type="assessment",
                input_id="retrieve-scales",
                pre_prompt=pre_prompt,
                post_prompt=None
            )
        except Exception as e:
            logging.error(f"Error in retrieve_scales: {e}")
            self.show_error(str(e))
        finally:
            self.is_loading = False

    # Event handlers
    @on(Button.Pressed, "#create-scales-button")
    async def handle_create_scales(
        self,
        event: Button.Pressed
    ) -> None:
        """Handle create scales button press."""
        logging.info(f"Creating initial scales for category '{self.selected_category}'")
        await self.retrieve_scales()

    @on(Select.Changed, "#scale-select")
    async def handle_scale_changed(
        self,
        event: Select.Changed
    ) -> None:
        """Handle scale selection changes."""
        if event.value != "":  # Assuming Select.BLANK is represented by an empty string
            self.selected_scale = event.value

    @on(Input.Submitted, "#scale-input")
    async def handle_scale_rename(
        self,
        event: Input.Submitted
    ) -> None:
        """Handle scale rename submission."""
        if not self.selected_scale or not self.selected_category:
            return

        new_name = event.value.strip()
        if not new_name:
            logging.warning("Attempted to rename scale to an empty string.")
            self.show_error("Scale name cannot be empty.")
            return

        logging.info(f"Renaming scale '{self.selected_scale}' to '{new_name}'")
        self._update_scale_name(self.selected_scale, new_name)
        self.selected_scale = new_name

    @on(TextArea.Changed, "#scale-description-area")
    async def handle_description_change(
        self,
        event: TextArea.Changed
    ) -> None:
        """Handle scale description changes."""
        if not self.selected_scale or not self.selected_category:
            return

        new_description = event.text_area.document.text.strip()
        self._update_scale_description(self.selected_scale, new_description)

    # LLM event handlers
    @on(LLMCallComplete)
    async def handle_llm_call_complete(
        self,
        event: LLMCallComplete
    ) -> None:
        """Handle LLM call completions."""
        if event.input_id == "retrieve-scales":
            await self._handle_scales_update(event.result)

    @on(LLMCallError)
    async def handle_llm_call_error(
        self,
        event: LLMCallError
    ) -> None:
        """Handle LLM call errors."""
        logging.error(f"LLM call error for {event.input_id}: {event.error}")
        self.show_error(event.error)
        self.is_loading = False

    # Scale data update methods
    async def _handle_scales_update(
        self,
        scales: List[Dict]
    ) -> None:
        """Handle scales update from LLM result."""
        try:
            # Update the scales in all_categories
            for cat in self.all_categories:
                if cat['name'] == self.selected_category:
                    cat['scale'] = scales
                    break
            
            # Update current scales (triggers watcher)
            self.current_scales = scales
            
            logging.debug(f"Scales updated for category '{self.selected_category}': {scales}")
        except Exception as e:
            logging.error(f"Error updating scales: {e}")
            self.show_error("Failed to update scales.")

    def _update_scale_name(
        self,
        old_name: str,
        new_name: str
    ) -> None:
        """Update scale name in data structures."""
        updated_scales = self.current_scales.copy()
        for scale in updated_scales:
            if scale['name'] == old_name:
                scale['name'] = new_name
                break
        self.current_scales = updated_scales  # Trigger watcher

        # Update in all_categories
        for cat in self.all_categories:
            if cat['name'] == self.selected_category:
                cat['scale'] = updated_scales
                break

    def _update_scale_description(
        self,
        scale_name: str,
        new_description: str
    ) -> None:
        """Update scale description in data structures."""
        updated_scales = self.current_scales.copy()
        for scale in updated_scales:
            if scale['name'] == scale_name:
                scale['description'] = new_description
                break
        self.current_scales = updated_scales  # Trigger watcher

        # Update in all_categories
        for cat in self.all_categories:
            if cat['name'] == self.selected_category:
                cat['scale'] = updated_scales
                break

    def show_error(self, message: str) -> None:
        """Display an error message to the user."""
        self.notify(message, severity="error")
        logging.error(message)

class SelectCategoryWidget(Static):
    """Widget for the UI components of categories."""
    
    # Reactive properties
    selected_category: Reactive[Optional[str]] = Reactive(None)
    is_loading: Reactive[bool] = Reactive(False)
    show_edit_controls: Reactive[bool] = Reactive(False)
    title_value: Reactive[str] = Reactive("")
    description_value: Reactive[str] = Reactive("")
    categories: Reactive[List[Dict]] = Reactive(default=[])
    
    def __init__(
        self,
        all_categories: Reactive[List[Dict]],
        agent_name: str,
        session_manager,
        screen_name: str,
        id: Optional[str] = None
    ):
        super().__init__(id=id)
        self.agent_name = agent_name
        self.all_categories = all_categories  # Reference to shared reactive property
        self.session_manager = session_manager
        self.screen_name = screen_name
        self._init_widgets()
    
    def _init_widgets(self) -> None:
        """Initialize all widget components."""
        self.select = Select(
            options=[("create_initial", "Create Initial Categories")],
            id="category-select"
        )
        
        self.loading_indicator = Static("Loading categories...", id="loading-indicator")
        self.input_box = Input(placeholder="Rename selected category", id="category-input")
        self.description_area = TextArea("", id="category-description-area")
        self.refresh_title_button = Button("Refresh Title", id="refresh-title-button")
        self.refresh_description_button = Button("Refresh Description", id="refresh-description-button")
        self.refresh_both_button = Button("Refresh Both", id="refresh-both-button")
        self.lbl_text = Label("Modify Directly or use buttons for agent assistance", id="lbl_text")
        
        # Set initial visibility
        self.loading_indicator.visible = False 
        self.input_box.visible = False
        self.description_area.visible = False
        self.refresh_title_button.visible = False
        self.refresh_description_button.visible = False
        self.refresh_both_button.visible = False
        self.lbl_text.visible = False
    
    async def on_mount(self) -> None:
        """Initialize components after mount."""
        self.llm_call_manager = LLMCallManager()
        self.llm_call_manager.set_message_post_target(self)
        logging.info(f"Post target message set to: {self.llm_call_manager._message_post_target}")
    
    def compose(self) -> ComposeResult:
        """Compose the widget layout."""
        yield self.select
        yield self.loading_indicator
        with Vertical(id="edit_container"):
            yield self.lbl_text
            yield self.input_box
            yield self.description_area
            with Horizontal(id="button-container"):
                yield self.refresh_title_button
                yield self.refresh_description_button
                yield self.refresh_both_button
    
    def update_category_details(self, title: str, description: str) -> None:
        """Update both title and description for the selected category."""
        self.title_value = title
        self.description_value = description
    
    def update_options(self, options: List[Tuple[str, str]]) -> None:
        """Helper method to update select options."""
        self.select.set_options(options)
        self.refresh()
    
    # Reactive watchers
    def watch_is_loading(
        self,
        old_value: bool,
        new_value: bool
    ) -> None:
        """React to loading state changes."""
        if self.loading_indicator:
            self.loading_indicator.visible = new_value
            # Hide other controls during loading
            if new_value:
                self.show_edit_controls = False
            self.refresh()
    
    def watch_show_edit_controls(
        self,
        old_value: bool,
        new_value: bool
    ) -> None:
        """React to edit controls visibility changes."""
        if not self.is_loading:  # Only show controls if not loading
            self.input_box.visible = new_value
            self.description_area.visible = new_value
            self.refresh_title_button.visible = new_value
            self.refresh_description_button.visible = new_value
            self.refresh_both_button.visible = new_value
            self.lbl_text.visible = new_value
            self.refresh()
    
    def watch_title_value(
        self,
        old_value: str,
        new_value: str
    ) -> None:
        """React to title value changes."""
        if new_value != self.input_box.value:
            self.input_box.value = new_value
            self.input_box.refresh()
    
    def watch_description_value(
        self,
        old_value: str,
        new_value: str
    ) -> None:
        """React to description value changes."""
        if new_value != self.description_area.value:
            self.description_area.value = new_value
            self.description_area.refresh()
    
    def watch_categories(
        self,
        old_value: List[Dict],
        new_value: List[Dict]
    ) -> None:
        """React to categories list changes."""
        if isinstance(new_value, list):
            options = [("refresh_all", "Refresh All")] + [
                (cat['name'], cat['name']) for cat in new_value if isinstance(cat, dict) and 'name' in cat
            ]
            self.select.set_options(options)
            self.refresh()
        else:
            logging.error(f"Invalid categories format: {type(new_value)}")
            self.show_error("Invalid categories format received")
    
    def watch_selected_category(
        self,
        old_value: Optional[str],
        new_value: Optional[str]
    ) -> None:
        """React to category selection changes."""
        if not new_value or new_value in ["create_initial", "refresh_all"]:
            self.show_edit_controls = False
            return
    
        # Set controls to be visible
        self.show_edit_controls = True
        
        # Update title and description based on selected category
        category_data = next(
            (cat for cat in self.categories if cat['name'] == new_value),
            None
        )
        if category_data:
            self.title_value = category_data.get('name', '')
            self.description_value = category_data.get('description', '')
    
    # LLM Configuration
    def _llm_config_current_agent(
        self
    ) -> Optional[Tuple[Dict[str, Any], str]]:
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
            pre_prompt = f"Please provide a new title for the category: {self.selected_category}"
            
            await self.llm_call_manager.submit_llm_call_with_agent(
                llm_function=send_agent_data_to_llm,
                llm_config=llm_config,
                agent_name=current_agent,
                agent_type="assessment",
                input_id="scale-title",
                pre_prompt=pre_prompt,
                post_prompt=None
            )
        except Exception as e:
            logging.error(f"Error in refresh_title: {e}")
            self.show_error(str(e))
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
            pre_prompt = f"Please provide a new description for the category: {self.selected_category}"
            
            await self.llm_call_manager.submit_llm_call_with_agent(
                llm_function=send_agent_data_to_llm,
                llm_config=llm_config,
                agent_name=current_agent,
                agent_type="assessment",
                input_id="scale-description",
                pre_prompt=pre_prompt,
                post_prompt=None
            )
        except Exception as e:
            logging.error(f"Error in refresh_description: {e}")
            self.show_error(str(e))
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
    def handle_category_selected(
        self,
        message: CategorySelected
    ) -> None:
        """Handle the CategorySelected message to set title and description."""
        self.title_value = message.category_name  # Update the title value
        self.input_box.value = self.title_value  # Set the input box with the title
        self.input_box.refresh()

        self.description_value = message.category_description  # Update the description value
        self.description_area.value = self.description_value  # Set the TextArea with the description
        self.description_area.refresh()   
    
    @on(LLMCallComplete)
    async def handle_llm_call_complete(
        self,
        event: LLMCallComplete
    ) -> None:
        """Handle LLM call completions."""
        handlers = {
            "scale-title": self._handle_title_update,
            "scale-description": self._handle_description_update,
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
    async def handle_llm_call_error(
        self,
        event: LLMCallError
    ) -> None:
        """Handle LLM call errors."""
        logging.error(f"LLM call error for {event.input_id}: {event.error}")
        self.show_error(event.error)
        self.is_loading = False
    
    @on(Button.Pressed)
    async def handle_button_press(
        self,
        event: Button.Pressed
    ) -> None:
        """Handle button press events."""
        handlers = {
            "refresh-title-button": self.refresh_title,
            "refresh-description-button": self.refresh_description,
            "refresh-both-button": self.refresh_both
        }
        
        handler = handlers.get(event.button.id)
        if handler:
            await handler()
    
    # LLM result handlers
    async def _handle_title_update(
        self,
        result: Any
    ) -> None:
        """Handle title update from LLM result."""
        if isinstance(result, list) and result:
            new_title = result[0].get('name', '')
            if new_title:
                self.title_value = new_title
    
    async def _handle_description_update(
        self,
        result: Any
    ) -> None:
        """Handle description update from LLM result."""
        if isinstance(result, list) and result:
            new_description = result[0].get('description', '')
            if new_description:
                self.description_value = new_description
    
    async def _handle_categories_update(
        self,
        result: Any
    ) -> None:
        """Handle categories update from LLM result."""
        if isinstance(result, list):
            self.categories = result
            # If there's a selected category, update its details
            if self.selected_category:
                category_data = next(
                    (cat for cat in result if cat['name'] == self.selected_category),
                    None
                )
                if category_data:
                    self.title_value = category_data.get('name', '')
                    self.description_value = category_data.get('description', '')
    
    async def _handle_scales_update(
        self,
        result: Any
    ) -> None:
        """Handle scales update from LLM result."""
        # Implement if needed
        pass

class ScaleWidget(SessionDependentUI):
    """Widget for managing scales within a selected category."""
    
    # Reactive properties
    selected_category: Reactive[Optional[str]] = Reactive(None)
    selected_scale: Reactive[Optional[str]] = Reactive(None)
    current_scales: Reactive[List[Dict]] = Reactive(default=[])
    is_loading: Reactive[bool] = Reactive(False)
    show_scales: Reactive[bool] = Reactive(False)

    def __init__(
        self,
        all_categories: Reactive[List[Dict]],
        agent_name: str,
        session_manager,
        screen_name: str,
        id: Optional[str] = None
    ):
        """Initialize the ScaleWidget."""
        super().__init__(session_manager, screen_name, agent_name)
        self.all_categories = all_categories  # Reference to shared categories
        self.agent_name = agent_name
        self.scale_components = SelectScaleWidget(
                all_categories,
                agent_name,
                session_manager,
                screen_name,
                id = None
        )

    def compose(self) -> ComposeResult:
        """Compose widget layout."""
        yield self.scale_components

    async def on_mount(self) -> None:
        """Initialize LLM manager after mount."""
        self.llm_call_manager = LLMCallManager()
        self.llm_call_manager.set_message_post_target(self)
        logging.info(f"Post target message set to: {self.llm_call_manager._message_post_target}")

    # Reactive Watchers
    def watch_selected_category(
        self,
        old_value: Optional[str],
        new_value: Optional[str]
    ) -> None:
        """React to category selection changes."""
        if new_value:
            asyncio.create_task(self._update_scales_for_category(new_value))

    def watch_current_scales(
        self,
        old_value: List[Dict],
        new_value: List[Dict]
    ) -> None:
        """React to changes in current scales."""
        self.scale_components.scales = new_value
        self.show_scales = bool(new_value)

    def watch_is_loading(
        self,
        old_value: bool,
        new_value: bool
    ) -> None:
        """React to loading state changes."""
        self.scale_components.is_loading = new_value

    def watch_selected_scale(
        self,
        old_value: Optional[str],
        new_value: Optional[str]
    ) -> None:
        """React to scale selection changes."""
        self.scale_components.selected_scale = new_value
        if new_value:
            self._update_scale_details(new_value)

    # Private helper methods
    async def _update_scales_for_category(
        self,
        category_name: str
    ) -> None:
        """Update scales for the selected category."""
        category_data = next(
            (cat for cat in self.all_categories if cat['name'] == category_name),
            None
        )
        if category_data:
            self.current_scales = category_data.get("scale", [])
            if not self.current_scales:
                # Show create button if no scales available
                self.scale_components.show_create_button = True
            else:
                self.scale_components.show_create_button = False

    def _update_scale_details(
        self,
        scale_name: str
    ) -> None:
        """Update the display of scale details."""
        scale_data = next(
            (scale for scale in self.current_scales if scale['name'] == scale_name),
            None
        )
        if scale_data:
            self.scale_components.title_value = scale_data.get('name', '')
            self.scale_components.description_value = scale_data.get('description', '')
            self.scale_components.description_area.refresh()

    def _llm_config_current_agent(
        self
    ) -> Optional[Tuple[Dict[str, Any], str]]:
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
            pre_prompt = f"Please provide scales for the category: {self.selected_category}"
            
            await self.llm_call_manager.submit_llm_call_with_agent(
                llm_function=send_agent_data_to_llm,
                llm_config=llm_config,
                agent_name=current_agent,
                agent_type="assessment",
                input_id="retrieve-scales",
                pre_prompt=pre_prompt,
                post_prompt=None
            )
        except Exception as e:
            logging.error(f"Error in retrieve_scales: {e}")
            self.show_error(str(e))
        finally:
            self.is_loading = False

    # Event handlers
    @on(Button.Pressed, "#create-scales-button")
    async def handle_create_scales(
        self,
        event: Button.Pressed
    ) -> None:
        """Handle create scales button press."""
        logging.info(f"Creating initial scales for category '{self.selected_category}'")
        await self.retrieve_scales()

    @on(Select.Changed, "#scale-select")
    async def handle_scale_changed(
        self,
        event: Select.Changed
    ) -> None:
        """Handle scale selection changes."""
        if event.value != "":  # Assuming Select.BLANK is represented by an empty string
            self.selected_scale = event.value

    @on(Input.Submitted, "#scale-input")
    async def handle_scale_rename(
        self,
        event: Input.Submitted
    ) -> None:
        """Handle scale rename submission."""
        if not self.selected_scale or not self.selected_category:
            return

        new_name = event.value.strip()
        if not new_name:
            logging.warning("Attempted to rename scale to an empty string.")
            self.show_error("Scale name cannot be empty.")
            return

        logging.info(f"Renaming scale '{self.selected_scale}' to '{new_name}'")
        self._update_scale_name(self.selected_scale, new_name)
        self.selected_scale = new_name

    @on(TextArea.Changed, "#scale-description-area")
    async def handle_description_change(
        self,
        event: TextArea.Changed
    ) -> None:
        """Handle scale description changes."""
        if not self.selected_scale or not self.selected_category:
            return

        new_description = event.text_area.document.text.strip()
        self._update_scale_description(self.selected_scale, new_description)

    # LLM event handlers
    @on(LLMCallComplete)
    async def handle_llm_call_complete(
        self,
        event: LLMCallComplete
    ) -> None:
        """Handle LLM call completions."""
        if event.input_id == "retrieve-scales":
            await self._handle_scales_update(event.result)

    @on(LLMCallError)
    async def handle_llm_call_error(
        self,
        event: LLMCallError
    ) -> None:
        """Handle LLM call errors."""
        logging.error(f"LLM call error for {event.input_id}: {event.error}")
        self.show_error(event.error)
        self.is_loading = False

    # Scale data update methods
    async def _handle_scales_update(
        self,
        scales: List[Dict]
    ) -> None:
        """Handle scales update from LLM result."""
        try:
            # Update the scales in all_categories
            for cat in self.all_categories:
                if cat['name'] == self.selected_category:
                    cat['scale'] = scales
                    break
            
            # Update current scales (triggers watcher)
            self.current_scales = scales
            
            logging.debug(f"Scales updated for category '{self.selected_category}': {scales}")
        except Exception as e:
            logging.error(f"Error updating scales: {e}")
            self.show_error("Failed to update scales.")

    def _update_scale_name(
        self,
        old_name: str,
        new_name: str
    ) -> None:
        """Update scale name in data structures."""
        updated_scales = self.current_scales.copy()
        for scale in updated_scales:
            if scale['name'] == old_name:
                scale['name'] = new_name
                break
        self.current_scales = updated_scales  # Trigger watcher

        # Update in all_categories
        for cat in self.all_categories:
            if cat['name'] == self.selected_category:
                cat['scale'] = updated_scales
                break

    def _update_scale_description(
        self,
        scale_name: str,
        new_description: str
    ) -> None:
        """Update scale description in data structures."""
        updated_scales = self.current_scales.copy()
        for scale in updated_scales:
            if scale['name'] == scale_name:
                scale['description'] = new_description
                break
        self.current_scales = updated_scales  # Trigger watcher

        # Update in all_categories
        for cat in self.all_categories:
            if cat['name'] == self.selected_category:
                cat['scale'] = updated_scales
                break

    def show_error(self, message: str) -> None:
        """Display an error message to the user."""
        self.notify(message, severity="error")
        logging.error(message)

class SelectScaleWidget(Static):
    """Widget for the UI components of scales."""
    
    # Reactive properties
    selected_scale: Reactive[Optional[str]] = Reactive(None)
    is_loading: Reactive[bool] = Reactive(False)
    show_edit_controls: Reactive[bool] = Reactive(False)
    scales: Reactive[List[Dict]] = Reactive(default=[])
    title_value: Reactive[str] = Reactive("")
    description_value: Reactive[str] = Reactive("")
    show_create_button: Reactive[bool] = Reactive(False)
    
    def __init__(
        self,
        all_categories: Reactive[List[Dict]],
        agent_name: str,
        session_manager,
        screen_name: str,
        id: Optional[str] = None
    ):
        super().__init__(id=id)
        self.agent_name = agent_name
        self.all_categories = all_categories  # Reference to shared reactive property
        self.session_manager = session_manager
        self.screen_name = screen_name
        self._init_widgets()
    
    def _init_widgets(self) -> None:
        """Initialize all widget components."""
        self.create_scales_button = Button("Create Initial Scales", id="create-scales-button")
        self.scale_select = Select([], id="scale-select")
        self.loading_indicator = Static("Loading scales...", id="scale-loading-indicator")
        self.scale_input_box = Input(placeholder="Rename selected scale", id="scale-input")
        self.scale_description_area = TextArea("", id="scale-description-area")
    
        # Set initial visibility
        self.loading_indicator.visible = False
        self.scale_input_box.visible = False
        self.scale_description_area.visible = False
    
    async def on_mount(self) -> None:
        """Initialize components after mount."""
        self.llm_call_manager = LLMCallManager()
        self.llm_call_manager.set_message_post_target(self)
        logging.info(f"Post target message set to: {self.llm_call_manager._message_post_target}")
    
    def compose(self) -> ComposeResult:
        """Compose the widget layout."""
        yield self.create_scales_button
        yield self.scale_select
        yield self.loading_indicator
        yield self.scale_input_box
        yield self.scale_description_area
    
    def update_category_details(self, title: str, description: str) -> None:
        """Update both title and description for the selected scale."""
        self.title_value = title
        self.description_value = description
    
    def update_options(self, options: List[Tuple[str, str]]) -> None:
        """Helper method to update select options."""
        self.scale_select.set_options(options)
        self.refresh()
    
    # Reactive watchers
    def watch_is_loading(
        self,
        old_value: bool,
        new_value: bool
    ) -> None:
        """React to loading state changes."""
        self.loading_indicator.visible = new_value
        if new_value:
            self.show_edit_controls = False
        self.refresh()
    
    def watch_show_edit_controls(
        self,
        old_value: bool,
        new_value: bool
    ) -> None:
        """React to edit controls visibility changes."""
        if not self.is_loading:
            self.scale_input_box.visible = new_value
            self.scale_description_area.visible = new_value
            self.refresh()
    
    def watch_scales(
        self,
        old_value: List[Dict],
        new_value: List[Dict]
    ) -> None:
        """React to scales list changes."""
        if isinstance(new_value, list):
            options = [("refresh_all", "Refresh All")] + [
                (scale['name'], scale['name']) for scale in new_value if isinstance(scale, dict) and 'name' in scale
            ]
            self.scale_select.set_options(options)
            self.scale_select.visible = bool(new_value)
            self.show_create_button = not bool(new_value)
            if new_value:
                self.selected_scale = new_value[0]['name']
            self.refresh()
        else:
            logging.error(f"Invalid scales format: {type(new_value)}")
            self.show_error("Invalid scales format received")
    
    def watch_show_create_button(
        self,
        old_value: bool,
        new_value: bool
    ) -> None:
        """React to create button visibility changes."""
        self.create_scales_button.visible = new_value
        self.refresh()
    
    def watch_title_value(
        self,
        old_value: str,
        new_value: str
    ) -> None:
        """React to title value changes."""
        if new_value != self.scale_input_box.value:
            self.scale_input_box.value = new_value
            self.scale_input_box.refresh()
    
    def watch_description_value(
        self,
        old_value: str,
        new_value: str
    ) -> None:
        """React to description value changes."""
        if new_value != self.scale_description_area.value:
            self.scale_description_area.value = new_value
            self.scale_description_area.refresh()
    
    def watch_selected_scale(
        self,
        old_value: Optional[str],
        new_value: Optional[str]
    ) -> None:
        """React to scale selection changes."""
        if not new_value:
            self.show_edit_controls = False
            return

        self.show_edit_controls = True
        scale_data = next(
            (scale for scale in self.scales if scale['name'] == new_value),
            None
        )
        if scale_data:
            self.title_value = scale_data.get('name', '')
            self.description_value = scale_data.get('description', '')
    
    # LLM Configuration
    def _llm_config_current_agent(
        self
    ) -> Optional[Tuple[Dict[str, Any], str]]:
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
            pre_prompt = f"Please provide a new title for the scale: {self.selected_scale}"
            
            await self.llm_call_manager.submit_llm_call_with_agent(
                llm_function=send_agent_data_to_llm,
                llm_config=llm_config,
                agent_name=current_agent,
                agent_type="assessment",
                input_id="scale-title",
                pre_prompt=pre_prompt,
                post_prompt=None
            )
        except Exception as e:
            logging.error(f"Error in refresh_title: {e}")
            self.show_error(str(e))
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
            pre_prompt = f"Please provide a new description for the scale: {self.selected_scale}"
            
            await self.llm_call_manager.submit_llm_call_with_agent(
                llm_function=send_agent_data_to_llm,
                llm_config=llm_config,
                agent_name=current_agent,
                agent_type="assessment",
                input_id="scale-description",
                pre_prompt=pre_prompt,
                post_prompt=None
            )
        except Exception as e:
            logging.error(f"Error in refresh_description: {e}")
            self.show_error(str(e))
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
    def handle_category_selected(
        self,
        message: CategorySelected
    ) -> None:
        """Handle the CategorySelected message to set title and description."""
        self.title_value = message.category_name  # Update the title value
        self.scale_input_box.value = self.title_value  # Set the input box with the title
        self.scale_input_box.refresh()

        self.description_value = message.category_description  # Update the description value
        self.scale_description_area.value = self.description_value  # Set the TextArea with the description
        self.scale_description_area.refresh()   
    
    @on(LLMCallComplete)
    async def handle_llm_call_complete(
        self,
        event: LLMCallComplete
    ) -> None:
        """Handle LLM call completions."""
        handlers = {
            "scale-title": self._handle_title_update,
            "scale-description": self._handle_description_update,
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
    async def handle_llm_call_error(
        self,
        event: LLMCallError
    ) -> None:
        """Handle LLM call errors."""
        logging.error(f"LLM call error for {event.input_id}: {event.error}")
        self.show_error(event.error)
        self.is_loading = False
    
    @on(Button.Pressed)
    async def handle_button_press(
        self,
        event: Button.Pressed
    ) -> None:
        """Handle button press events."""
        handlers = {
            "refresh-title-button": self.refresh_title,
            "refresh-description-button": self.refresh_description,
            "refresh-both-button": self.refresh_both
        }
        
        handler = handlers.get(event.button.id)
        if handler:
            await handler()
    
    # LLM result handlers
    async def _handle_title_update(
        self,
        result: Any
    ) -> None:
        """Handle title update from LLM result."""
        if isinstance(result, list) and result:
            new_title = result[0].get('name', '')
            if new_title:
                self.title_value = new_title
    
    async def _handle_description_update(
        self,
        result: Any
    ) -> None:
        """Handle description update from LLM result."""
        if isinstance(result, list) and result:
            new_description = result[0].get('description', '')
            if new_description:
                self.description_value = new_description
    
    async def _handle_categories_update(
        self,
        result: Any
    ) -> None:
        """Handle categories update from LLM result."""
        if isinstance(result, list):
            self.scales = result
            # If there's a selected scale, update its details
            if self.selected_scale:
                scale_data = next(
                    (scale for scale in result if scale['name'] == self.selected_scale),
                    None
                )
                if scale_data:
                    self.title_value = scale_data.get('name', '')
                    self.description_value = scale_data.get('description', '')
    
    async def _handle_scales_update(
        self,
        result: Any
    ) -> None:
        """Handle scales update from LLM result."""
        # Implement if needed
        pass
    
    def show_error(self, message: str) -> None:
        """Display an error message to the user."""
        self.notify(message, severity="error")
        logging.error(message)
