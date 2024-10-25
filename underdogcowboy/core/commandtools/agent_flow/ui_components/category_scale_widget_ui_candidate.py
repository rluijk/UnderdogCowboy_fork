import logging
import asyncio

from typing import Tuple, Optional, Dict, Any

from concurrent.futures import ThreadPoolExecutor

from textual import on
from textual.app import App, ComposeResult
from textual.containers import Vertical, Horizontal
from textual.widgets import Label, Header, Select, Input, Static, TextArea, Button
from textual.message import Message

# LLM
from agent_llm_handler import send_agent_data_to_llm, run_category_call 
from llm_call_manager import LLMCallManager

# Events
from events.llm_events import LLMCallComplete, LLMCallError

# UC
from underdogcowboy.core.agent import Agent

class CategorySelected(Message):
    """Custom message to indicate a category has been selected."""
    def __init__(self, sender, category_name: str):
        super().__init__()
        self.sender = sender
        self.category_name = category_name

class SelectCategoryWidget(Static):
    """Widget for the UI components of categories."""
    def __init__(self, agent_name_plain):
        super().__init__()
        self.selected_category = None  # Initialize to track the selected category
        
        self.agent_name_plain = agent_name_plain
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

        
    def on_mount(self) -> None:
        self.llm_call_manager = LLMCallManager()
        self.llm_call_manager.set_message_post_target(self)
        logging.info(f"Post target message set to: {self.llm_call_manager._message_post_target}")

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

    def _llm_config_current_agent(self) -> Optional[Tuple[Dict[str, Any], str]]:
        llm_config = self.app.get_current_llm_config()
        if not llm_config:
            self.show_error("No LLM configuration available.")
            return
        
        current_agent = self.agent_name_plain
        if not current_agent:
            self.show_error("No agent currently loaded. Please load an agent first.")
            return

        return (llm_config, current_agent)

    """  --------- Start Base pattern  ---------- """
    """  method via async and event system that contains the pre prompt """
    """  LLMComplete and LLMError handlers  """

    async def refresh_title(self) -> None:
        llm_config, current_agent = self._llm_config_current_agent()
        if not llm_config or not current_agent:
            return  # Early exit if configuration is missing

        pre_prompt = f"prompt to get a title: {self.selected_category}"
        
        async def task_wrapper():
            try:
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
                logging.error(f"Error in refresh_title task: {e}")
                self.show_error(str(e))
        
        asyncio.create_task(task_wrapper())

    async def refresh_description(self) -> None:
        llm_config, current_agent = self._llm_config_current_agent()
        if not llm_config or not current_agent:
            return  # Early exit if configuration is missing

        pre_prompt = f"prompt to get a description: {self.selected_category}"
        
        async def task_wrapper():
            try:
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
                logging.error(f"Error in refresh_description task: {e}")
                self.show_error(str(e))
        
        asyncio.create_task(task_wrapper())

    async def refresh_both(self):
        """Function to refresh both title and description concurrently."""
        llm_config, current_agent = self._llm_config_current_agent()
        if not llm_config or not current_agent:
            return  # Early exit if configuration is missing

        pre_prompt_title = f"prompt to get a title: {self.selected_category}"
        pre_prompt_description = f"prompt to get a description: {self.selected_category}"

        async def task_wrapper():
            try:
                await asyncio.gather(
                    self.llm_call_manager.submit_llm_call_with_agent( 
                        llm_function=send_agent_data_to_llm,
                        llm_config=llm_config,
                        agent_name=current_agent,
                        agent_type="assessment",
                        input_id="scale-title",
                        pre_prompt=pre_prompt_title,    
                        post_prompt=None
                    ),
                    self.llm_call_manager.submit_llm_call_with_agent( 
                        llm_function=send_agent_data_to_llm,
                        llm_config=llm_config,
                        agent_name=current_agent,
                        agent_type="assessment",
                        input_id="scale-description",
                        pre_prompt=pre_prompt_description,    
                        post_prompt=None
                    )
                )
            except Exception as e:
                logging.error(f"Error in refresh_both task: {e}")
                self.show_error(str(e))
        
        asyncio.create_task(task_wrapper())

    @on(LLMCallComplete)
    async def handle_llm_call_complete(self, event: LLMCallComplete) -> None:
        logging.info(f"LLMCallComplete with event.input_id: {event.input_id}")
        if event.input_id == "scale-title":
            await self.on_refresh_title_complete(event)
        elif event.input_id == "scale-description":
            await self.on_refresh_description_complete(event)
  #      elif event.input_id == "create-initial-categories":
  #          await self.on_create_initial_categories_complete(event)
        elif event.input_id == "refresh-categories":
            await self.on_refresh_categories_complete(event)
        elif event.input_id == "retrieve-scales":
            await self.on_retrieve_scales_complete(event)

    async def on_refresh_title_complete(self, event: LLMCallComplete) -> None:
        if event.input_id == "scale-title":
            try:
                self.input_box.value = event.result[0]['name']
                self.input_box.refresh()
            except (IndexError, KeyError) as e:
                logging.error(f"Error processing scale-title result: {e}")
                self.show_error("Invalid data received for title.")

    async def on_refresh_description_complete(self, event: LLMCallComplete) -> None:
        if event.input_id == "scale-description":
            try:
                self.description_area.value = event.result[0]['description']
                self.description_area.refresh()
            except (IndexError, KeyError) as e:
                logging.error(f"Error processing scale-description result: {e}")
                self.show_error("Invalid data received for description.")

    async def on_refresh_categories_complete(self, event: LLMCallComplete) -> None:
        if event.input_id == "refresh-categories":
            try:
                categories = event.result
                self.retrieve_categories(categories)
            except Exception as e:
                logging.error(f"Error processing refresh-categories result: {e}")
                self.show_error("Failed to refresh categories.")

    async def on_retrieve_scales_complete(self, event: LLMCallComplete) -> None:
        if event.input_id == "retrieve-scales":
            try:
                scales = event.result
                for cat in self.all_categories:
                    if cat['name'] == self.selected_category:
                        cat['scale'] = scales
                        break
                self.current_scales = scales
                self.scale_components.scale_select.set_options([(scale['name'], scale['name']) for scale in scales])
                if scales:
                    self.scale_components.scale_select.value = scales[0]['name']
                    self.display_scale_details(scales[0]['name'])
                logging.debug(f"Scales retrieved for category '{self.selected_category}': {scales}")
            except Exception as e:
                logging.error(f"Error retrieving scales for category '{self.selected_category}': {e}")
                self.show_error("Failed to retrieve scales.")
            finally:
                self.scale_components.loading_indicator.visible = False
                self.refresh()

    @on(LLMCallError)
    async def handle_llm_call_error(self, event: LLMCallError) -> None:
        if event.input_id == "scale-title":
            await self.on_refresh_title_error(event)
        elif event.input_id == "scale-description":
            await self.on_refresh_description_error(event)
#        elif event.input_id == "create-initial-categories":
#            await self.on_create_initial_categories_error(event)
        elif event.input_id == "refresh-categories":
            await self.on_refresh_categories_error(event)
        elif event.input_id == "retrieve-scales":
            await self.on_retrieve_scales_error(event)

    async def on_refresh_title_error(self, event: LLMCallError) -> None:
        if event.input_id == "scale-title":    
            self.show_error(event.error)

    async def on_refresh_description_error(self, event: LLMCallError) -> None:
        if event.input_id == "scale-description":    
            self.show_error(event.error)

    async def on_create_initial_categories_error(self, event: LLMCallError) -> None:
        if event.input_id == "create-initial-categories":    
            self.show_error(event.error)

    async def on_refresh_categories_error(self, event: LLMCallError) -> None:
        if event.input_id == "refresh-categories":    
            self.show_error(event.error)

    async def on_retrieve_scales_error(self, event: LLMCallError) -> None:
        if event.input_id == "retrieve-scales":    
            self.show_error(event.error)

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events."""
        button_id = event.button.id
        if button_id == "refresh-title-button":
            await self.refresh_title()
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

    async def show_loading_indicator(self):
        """Utility method to show the loading indicator."""
        self.loading_indicator.visible = True
        self.refresh()

    async def hide_loading_indicator(self):
        """Utility method to hide the loading indicator."""
        self.loading_indicator.visible = False
        self.refresh()

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
    def __init__(self, all_categories, agent_name_plain, id=None):
        super().__init__(id=id)
        self.selected_category = None
       
        self.all_categories = all_categories  # Datastructure passed via init
        self.agent_name_plain = agent_name_plain
        self.category_components = SelectCategoryWidget(agent_name_plain)
       

    def compose(self) -> ComposeResult:
        yield self.category_components

    def on_mount(self) -> None:
        self.llm_call_manager = LLMCallManager()
        self.llm_call_manager.set_message_post_target(self)
        logging.info(f"Post target message set to: {self.llm_call_manager._message_post_target}")


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
            llm_config, current_agent = self.category_components._llm_config_current_agent()
            if not llm_config or not current_agent:
                return  # Early exit if configuration is missing

            pre_prompt = f"prompt to get initial categories"
            
            await self.category_components.show_loading_indicator()
            self.category_components.select.set_options([("waiting", "Waiting for categories...")])
            self.category_components.hide_buttons()  

            async def task_wrapper():
                try:
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
                    logging.error(f"Error in create_initial_categories task: {e}")
                    self.show_error(str(e))
            
            asyncio.create_task(task_wrapper())

        elif selected_value == "Refresh All":
            llm_config, current_agent = self.category_components._llm_config_current_agent()
            if not llm_config or not current_agent:
                return  # Early exit if configuration is missing

            pre_prompt = f"prompt to refesh all"
            
            await self.category_components.show_loading_indicator()
            self.category_components.select.set_options([("waiting", "Refreshing categories...")])
            self.category_components.hide_buttons()  

            async def task_wrapper():
                try:
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
                    logging.error(f"Error in refresh_categories task: {e}")
                    self.show_error(str(e))
            
            asyncio.create_task(task_wrapper())

        else:
            self.selected_category = selected_value
            self.category_components.input_box.value = selected_value
            self.category_components.input_box.visible = True

            selected_category_data = next(
                (cat for cat in self.all_categories if cat['name'] == selected_value), None
            )
            if selected_category_data:
                self.category_components.description_area.text = selected_category_data.get("description", "")
                self.category_components.description_area.visible = True
                self.category_components.description_area.refresh()

                self.category_components.show_buttons()  # Show buttons when a valid category is selected
                self.post_message(CategorySelected(self, self.selected_category))
            else:
                self.category_components.description_area.text = "Category not found."
                self.category_components.description_area.visible = True
                self.category_components.show_buttons()  # Optionally show buttons even if category not found

        self.refresh()

    @on(LLMCallComplete)
    async def handle_llm_call_complete(self, event: LLMCallComplete) -> None:
        logging.info(f"LLMCallComplete with event.input_id: {event.input_id}")
        if event.input_id == "create-initial-categories":
            self.on_create_initial_categories_complete(event)
  

    def on_create_initial_categories_complete(self, event: LLMCallComplete) -> None:
        if event.input_id == "create-initial-categories":
            try:
                categories = event.result
                self.retrieve_new_categories(categories)
            except Exception as e:
                logging.error(f"Error processing create-initial-categories result: {e}")
                self.show_error("Failed to create initial categories.")


    @on(Input.Submitted, "#category-input")
    async def category_input_submitted(self, event: Input.Submitted) -> None:
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
    async def category_description_changed(self, event: TextArea.Changed) -> None:
        if self.selected_category:
            new_description = event.text_area.document.text.strip()
            logging.info(f"Updating description for category '{self.selected_category}'")
            for cat in self.all_categories:
                if cat['name'] == self.selected_category:
                    cat['description'] = new_description
                    break
            self.refresh()

    def retrieve_categories_common(self, categories, category_type="categories"):
        """
        Generalized method to retrieve categories.

        :param categories: List of category dictionaries.
        :param category_type: Type of categories being retrieved (e.g., "categories", "new categories").
        """
        logging.debug(f"debugging: {categories}")
        try:
            self.all_categories = categories
            self.category_components.select.set_options(
                [("refresh_all", "Refresh All")] + [(cat['name'], cat['name']) for cat in self.all_categories]
            )
            self.category_components.select.value = categories[0]['name'] if categories else None
            # After successfully retrieving categories, show buttons
            self.category_components.show_buttons()
        except Exception as e:
            logging.error(f"Error retrieving {category_type}: {e}")
            self.category_components.select.set_options([("error", f"Error loading {category_type}")])
            # Hide buttons on error
            self.category_components.hide_buttons()
        finally:
            asyncio.create_task(self.category_components.hide_loading_indicator())
            self.refresh()

    def retrieve_new_categories(self, categories):
        """Retrieve and update new categories."""
        self.retrieve_categories_common(categories, category_type="new categories")

    def retrieve_categories(self, categories):
        """Retrieve and update existing categories."""
        self.retrieve_categories_common(categories, category_type="categories")

class ScaleWidget(Static):
    """Widget for managing scales within a selected category."""
    def __init__(self, all_categories, agent_name_plain, id=None):
        super().__init__(id=id)
   
        self.all_categories = all_categories  # Reference to the categories data structure
        self.selected_category = None
        self.current_scales = []
        self.selected_scale = None
        self.scale_components = SelectScaleWidget()
        self.agent_name_plain = agent_name_plain

    def compose(self) -> ComposeResult:
        yield self.scale_components


    def on_mount(self) -> None:
        self.llm_call_manager = LLMCallManager()
        self.llm_call_manager.set_message_post_target(self)
        logging.info(f"Post target message set to: {self.llm_call_manager._message_post_target}")

    async def update_scales(self, selected_category_name):
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
        await self.retrieve_scales()

    async def retrieve_scales(self):
        llm_config, current_agent = self._llm_config_current_agent()
        if not llm_config or not current_agent:
            return  # Early exit if configuration is missing

        pre_prompt = f"prompt to retrieve scales"
        
    
        async def task_wrapper():
            try:
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
                logging.error(f"Error in retrieve_scales task: {e}")
                self.show_error(str(e))
        
        asyncio.create_task(task_wrapper())

    @on(LLMCallComplete)
    async def handle_llm_call_complete(self, event: LLMCallComplete) -> None:
        if event.input_id == "retrieve-scales":
            await self.on_retrieve_scales_complete(event)

    async def on_retrieve_scales_complete(self, event: LLMCallComplete) -> None:
        if event.input_id == "retrieve-scales":
            try:
                scales = event.result
                for cat in self.all_categories:
                    if cat['name'] == self.selected_category:
                        cat['scale'] = scales
                        break
                self.current_scales = scales
                self.scale_components.scale_select.set_options([(scale['name'], scale['name']) for scale in scales])
                if scales:
                    self.scale_components.scale_select.value = scales[0]['name']
                    self.display_scale_details(scales[0]['name'])
                logging.debug(f"Scales retrieved for category '{self.selected_category}': {scales}")
            except Exception as e:
                logging.error(f"Error retrieving scales for category '{self.selected_category}': {e}")
                self.show_error("Failed to retrieve scales.")
            finally:
                self.scale_components.loading_indicator.visible = False
                self.refresh()

    @on(LLMCallError)
    async def handle_llm_call_error(self, event: LLMCallError) -> None:
        if event.input_id == "retrieve-scales":
            await self.on_retrieve_scales_error(event)

    async def on_retrieve_scales_error(self, event: LLMCallError) -> None:
        if event.input_id == "retrieve-scales":    
            self.show_error(event.error)

    def display_scale_details(self, scale_name):
        """Display details of the selected scale."""
        self.selected_scale = scale_name
        selected_scale_data = next(
            (scale for scale in self.current_scales if scale['name'] == scale_name), None
        )
        if selected_scale_data:
            self.scale_components.scale_input_box.value = selected_scale_data.get('name', '')
            self.scale_components.scale_description_area.text = selected_scale_data.get('description', '')
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
    async def scale_input_submitted(self, event: Input.Submitted) -> None:
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
    async def scale_description_changed(self, event: TextArea.Changed) -> None:
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
    def __init__(self, agent_name_plain, id=None):
        super().__init__(id=id)

        self.all_categories = []
        self.agent_name_plain = agent_name_plain
        self.category_widget = CategoryWidget(self.all_categories, self.agent_name_plain,  id="category-widget")
        self.scale_widget = ScaleWidget(self.all_categories, self.agent_name_plain, id="scale-widget")

    def compose(self) -> ComposeResult:
        with Vertical(id="main-container"):
            yield self.category_widget
            yield self.scale_widget

    def on_category_selected(self, message: CategorySelected) -> None:
        """Handle CategorySelected messages from CategoryWidget."""
        asyncio.create_task(self.scale_widget.update_scales(message.category_name))  # Ensure coroutine is run

class MainApp(App):
    CSS_PATH = "../mocks/category_widgets.css"

    def __init__(self):
        super().__init__()
  
        self.all_categories = []  # Initialize with an empty data structure
        logging.debug("MainApp initialized")

    def compose(self) -> ComposeResult:
        yield CategoryScaleWidget()

#if __name__ == "__main__":
#    logging.info("Starting MainApp")
#    app = MainApp()
#    app.run()
