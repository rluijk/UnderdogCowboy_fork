import logging
import os
import json
import re


from textual import on
from textual.app import ComposeResult
from textual.containers import Vertical, Horizontal
from textual.widgets import Header, Footer, Collapsible, Static
from textual.reactive import reactive
from textual.css.query import NoMatches
from textual.binding import Binding

from uccli import StateMachine

# Storage Interface and SessionManager
from session_manager import SessionManager

# UI Components
from ui_factory import UIFactory
from ui_components.dynamic_container import DynamicContainer
from ui_components.state_button_grid_ui import StateButtonGrid
from ui_components.state_info_ui import StateInfo
from ui_components.center_content_ui import CenterContent
from ui_components.chat_ui import ChatUI
# from ui_components.chat_ui_candidate import ChatUI

# from ui_components.left_side_ui import LeftSideContainer

from ui_components.load_agent_ui import LoadAgentUI
from ui_components.new_agent_ui import NewAgentUI
from ui_components.load_dialog_ui  import LoadDialogUI
from ui_components.new_dialog_ui import NewDialogUI

# Events
from events.button_events import UIButtonPressed
from events.agent_events import AgentSelected, NewAgentCreated
from events.dialog_events import DialogSelected, NewDialogCreated
from events.action_events import ActionSelected

# Screens
from screens.session_screen import SessionScreen

# State Machines
from state_machines.timeline_editor_state_machine import create_timeline_editor_state_machine

# uc
from underdogcowboy.core.config_manager import LLMConfigManager 
from underdogcowboy.core.json_storage import TimelineStorage

# uc exceptions
from underdogcowboy.core.exceptions import InvalidAgentNameError

class TimeLineEditorScreen(SessionScreen):
    """A screen for the timeline editor."""

    # CSS_PATH = "../state_machine_app.css"

    BINDINGS = [
        Binding("ctrl+t", "toggle_task_panel", "Toggle Task Panel")
    ]

    def __init__(self,
                 state_machine: StateMachine = None,
                 session_manager: SessionManager = None,
                 *args, **kwargs
                 ):
        
        super().__init__(*args, **kwargs)

        self.title = "Timeline Editor"
        self.state_machine = state_machine or create_timeline_editor_state_machine()
        self.session_manager = session_manager
        self.ui_factory = UIFactory(self)
        self.screen_name = "TimeLineEditorScreen"
        self.config_manager = LLMConfigManager()
        self._pending_session_manager = None
        self.timeline = None
        self.processor = None
        self.storage = TimelineStorage()

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(id="agent-centre", classes="dynamic-spacer"):
            yield DynamicContainer(id="center-dynamic-container-timeline-editor", classes="center-dynamic-spacer")        

        with Vertical(id="app-layout"):
            with Collapsible(title="Task Panel", id="state-info-collapsible", collapsed=False):                  
                yield StateInfo(id="state-info")
                yield StateButtonGrid(self.state_machine, id="button-grid", state_machine_active_on_mount=True)  
                
        yield Footer(id="footer", name="footer")

    def on_mount(self) -> None:
        logging.info("TimeLineEditorScreen on_mount called")
        state_info = self.query_one("#state-info", StateInfo)
        state_info.update_state_info(self.state_machine, "")
        self.update_header()

        # Apply pending session manager after widgets are ready
        if self._pending_session_manager:
            session_manager = self._pending_session_manager
            self._pending_session_manager = None
            self.call_later(self.set_session_manager, session_manager)

    def set_session_manager(self, new_session_manager: SessionManager):
        self.session_manager = new_session_manager
        if self.is_mounted:
            self.call_later(self.update_ui_after_session_load)
        else:
            self._pending_session_manager = new_session_manager


    def update_header(self, session_name=None, name=None):
        if not session_name:
            session_name = self.session_manager.current_session_name
        if not name:
            name = ""
        self.sub_title = f"{name}"
        if session_name:
            self.sub_title += f" - Active Session: {session_name}"
        self.refresh(layout=True)

    def action_toggle_task_panel(self) -> None:
        collapsible = self.query_one("#state-info-collapsible", Collapsible)
        collapsible.collapsed = not collapsible.collapsed

    on(DialogSelected)
    def on_dialog_selected(self, event: DialogSelected):
        self.current_dialog = event.dialog_name
        self.notify(f"Loaded Dialog: {event.dialog_name}")
        
        dynamic_container = self.query_one("#center-dynamic-container-timeline-editor", DynamicContainer)
        dynamic_container.clear_content()
        
        self.update_header(name=event.dialog_name.plain)
        self.load_chat_ui(self.current_dialog,"dialog")
        
        self.state_machine.current_state = self.state_machine.states["dialog_loaded"]
        self.query_one(StateInfo).update_state_info(self.state_machine, "")
        self.query_one(StateButtonGrid).update_buttons()


    on(AgentSelected)
    def on_agent_selected(self, event: AgentSelected):
        self.current_agent = event.agent_name.plain
        self.agent_name_plain = event.agent_name.plain
        self.notify(f"Loaded Agent: {event.agent_name.plain}")
       
        dynamic_container = self.query_one("#center-dynamic-container-timeline-editor", DynamicContainer)
        dynamic_container.clear_content()
        
        self.update_header(name=event.agent_name.plain)
        self.load_chat_ui(self.agent_name_plain, "agent")

        self.state_machine.current_state = self.state_machine.states["agent_loaded"]
        self.query_one(StateInfo).update_state_info(self.state_machine, "")
        self.query_one(StateButtonGrid).update_buttons()


    def load_chat_ui(self, name: str, type: str):
        id = 'chat-gui'
        try:
            # Use the UI factory to get the corresponding UI class and action based on the id
            ui_class, action = self.ui_factory.ui_factory(id)

            # Load the UI component if the factory returns one
            if ui_class:
                ui_instance = ui_class(name=name,type=type)
                dynamic_container = self.query_one("#center-dynamic-container-timeline-editor", DynamicContainer)
                dynamic_container.load_content(ui_instance)

            # Execute the action if provided
            if action:
                action()

        except ValueError as e:
            logging.error(f"Error: {e}")
    
    @on(UIButtonPressed)
    def handle_event_and_load_ui(self, event: UIButtonPressed) -> None:
        # Determine the appropriate id based on the event type
        logging.debug(f"Handler 'handle_event_and_load_ui' invoked with button_id: {event.button_id}")
        button_id = event.button_id
       
        dynamic_container = self.query_one("#center-dynamic-container-timeline-editor", DynamicContainer)
        dynamic_container.clear_content()

        try:
            # Use the UI factory to get the corresponding UI class and action based on the id
            ui_class, action = self.ui_factory.ui_factory(button_id)

            # Load the UI component if the factory returns one
            if ui_class:
                if button_id == "load-session" and not self.session_manager.list_sessions():
                    self.notify("No sessions available. Create a new session first.", severity="warning")
                else:
                    ui_instance = ui_class()
                    dynamic_container.load_content(ui_instance)

            # Execute the action if provided
            if action:
                action()

        except ValueError as e:
            logging.error(f"Error: {e}")

    # I think can be removed is SessionManager is not user in the timeline editor
    # which seems to be a close decision to be made. 
    def update_ui_after_session_load(self):
        try:
            dynamic_container = self.query_one("#center-dynamic-container-timeline-editor", DynamicContainer)
            dynamic_container.clear_content()

            stored_state = self.session_manager.get_data("current_state", screen_name=self.screen_name)
            if stored_state and stored_state in self.state_machine.states:
                self.state_machine.current_state = self.state_machine.states[stored_state]
            else:
                self.state_machine.current_state = self.state_machine.states["initial"]

            self.query_one(StateInfo).update_state_info(self.state_machine, "")
            self.query_one(StateButtonGrid).update_buttons()
            self.update_header()
        except NoMatches:
            logging.warning("Dynamic container not found; scheduling UI update later.")
            self.call_later(self.update_ui_after_session_load)

    @on(NewAgentCreated)
    def create_new_agent(self, event: NewAgentCreated):
        # Create agent in file system. 
        self._save_new_agent(event.agent_name)        
        dynamic_container: DynamicContainer = self.query_one("#center-dynamic-container-timeline-editor", DynamicContainer)
        dynamic_container.clear_content()

    @on(NewDialogCreated)
    def create_new_dialog(self, event: NewDialogCreated):
        # This is for dialog
        # dialog_save_path: str = self.config_manager.get_general_config().get('dialog_save_path', '')
        config_manager: LLMConfigManager = LLMConfigManager()
        dialog_path: str = config_manager.get_general_config().get('dialog_save_path', '')
        self._save_new_dialog(dialog_path, event.dialog_name)
        dynamic_container: DynamicContainer = self.query_one("#center-dynamic-container-timeline-editor", DynamicContainer)
        dynamic_container.clear_content()

    def _save_new_dialog(self, dialog_path, name):
        self.storage.save_new_dialog(name, dialog_path)

    def _save_new_agent(self, agent_name):
        try:
            self.storage.save_new_agent(agent_name)
        except ValueError as e:
            raise InvalidAgentNameError(agent_name) from e   

    def __back___save_new_dialog(self,dialog_path, name):
        
        # Create the directory if it doesn't exist
        os.makedirs(dialog_path, exist_ok=True)
        file_path = os.path.join(dialog_path, f"{name}.json")        
        
        # Metadata now includes name and description
        metadata = {
            "frozenSegments": [],
            "startMode": 'interactive',
            "name": name,
            "description": ""
        }
        
        # Prepare the data dictionary with additional metadata
        data = {
            "history": [],
            "metadata": metadata,
            "system_message": ""
        }
        # Writing to file
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)    

    def __bck___save_new_agent(self, agent_name):
        """Saves the current dialog as a user-defined agent."""
    

        # Remove extension if present
        filename_no_ext, ext = os.path.splitext(agent_name)

        # Python module name validation
        if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", filename_no_ext):
            raise InvalidAgentNameError(filename_no_ext)


        # File path construction
        agents_dir = os.path.expanduser("~/.underdogcowboy/agents")
    
        # Create the directory if it doesn't exist
        os.makedirs(agents_dir, exist_ok=True)
        file_path = os.path.join(agents_dir, f"{filename_no_ext}.json")
        

        # Metadata now includes name and description
        metadata = {
            "frozenSegments": [],
            "startMode": 'interactive',
            "name": filename_no_ext,
            "description": ""
        }

        # Prepare the data dictionary with additional metadata
        data = {
            "history": [],
            "metadata": metadata,
            "system_message": ""
        }

        # Writing to file
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

        # Reload agents to make the new agent available
        # from underdogcowboy import _reload_agents
        #_reload_agents() 

    def save_dialog(self):
        try:
            chat_ui = self.query_one(ChatUI)
            # Call the save_dialog method directly
            chat_ui.save_dialog()
        except NoMatches:
            logging.warning("ChatUI not found; cannot save dialog.")

    def save_agent(self):
        try:
            chat_ui = self.query_one(ChatUI)
            # Call the save_agent method directly
            chat_ui.save_agent()
        except NoMatches:
            logging.warning("ChatUI not found; cannot save agent.")


    def on_action_selected(self, event: ActionSelected) -> None:
        action = event.action

        if action == "save_dialog":
            self.save_dialog()
            return

        if action == "save_agent":
            self.save_agent()
            return
        
        if action == "reset":
            self.state_machine.current_state = self.state_machine.states["initial"]
            self.query_one(StateInfo).update_state_info(self.state_machine, "")
            self.query_one(StateButtonGrid).update_buttons()


        dynamic_container = self.query_one("#center-dynamic-container-timeline-editor", DynamicContainer)
        dynamic_container.clear_content()

        # Mapping actions to their respective UI classes
        ui_class = {
            "load_agent": LoadAgentUI,
            "load_dialog": LoadDialogUI,
            "new_dialog": NewDialogUI,
            "new_agent": NewAgentUI,
        }.get(action)

        if ui_class:
            dynamic_container.mount(ui_class())
        else:
            # For other actions, load generic content as before
            dynamic_container.mount(CenterContent(action))

