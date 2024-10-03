from typing import Dict, List, Set
import logging

from textual import on
from textual.screen import Screen
from textual.app import App, ComposeResult
from textual.containers import Vertical, Horizontal
from textual.widgets import  (  Label, Header, Footer, Collapsible )
from textual.css.query import NoMatches

from uccli import StateMachine  # Removed StorageManager import
from underdogcowboy.core.config_manager import LLMConfigManager 

""" imports clarity sytem """
# utils
from agent_llm_handler import send_agent_data_to_llm

# Storage
from session_manager import SessionManager

# Configs
from llm_manager import LLMManager

# UI
from ui_factory import UIFactory
from ui_components.system_message_ui import SystemMessageUI
from ui_components.dynamic_container import DynamicContainer
from ui_components.analyze_ui import AnalyzeUI 
from ui_components.feedback_input_ui import FeedbackInputUI
from ui_components.feedback_output_ui import FeedbackOutputUI
from ui_components.feedback_rules_ui import FeedbackRulesUI
from ui_components.feedback_constraints_ui import FeedbackConstraintsUI
from ui_components.load_agent_ui import LoadAgentUI
from ui_components.state_button_grid_ui import StateButtonGrid 
from ui_components.state_info_ui import StateInfo
from ui_components.center_content_ui import CenterContent
from ui_components.left_side_ui import LeftSideContainer

# Events
from events.button_events import UIButtonPressed
from events.agent_events import AgentSelected
from events.session_events import SessionSelected, NewSessionCreated, SessionSyncStopped
from events.action_events import ActionSelected

# Screens
from screens.session_screen import SessionScreen

# State Machines for each screen
from state_machines.clarity_state_machine import create_clarity_state_machine

from state_management.json_storage_manager import JSONStorageManager
from state_management.storage_interface import StorageInterface

class ClarityScreen(SessionScreen):

    CSS_PATH = "../state_machine_app.css"

    def __init__(self, storage_interface: StorageInterface = None, 
                 state_machine: StateMachine = None, 
                 session_manager: SessionManager = None,
                 *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.state_machine = state_machine or create_clarity_state_machine()
        self.storage_interface = storage_interface or JSONStorageManager()
        self.session_manager = session_manager or SessionManager(self.storage_interface)  
        self.ui_factory = UIFactory(self)
        
        self.current_agent = None
        self.agent_name_plain = None
        self.title = "Agent Clarity"
        
        # Initialize LLMManager
        self.llm_manager = LLMManager(
            config_manager=LLMConfigManager(),
            default_provider='anthropic',
            default_model_id='claude-3-5-sonnet-20240620',
            default_model_name='Claude 3.5 Sonnet'
        )
        
        # Set the default LLM during initialization
        self.llm_manager.set_default_llm()
            
        # Define the screen name for namespacing
        self.screen_name = "ClarityScreen"

        self._pending_session_manager = None

    def configure_default_llm(self):
        """Trigger the configuration process for the default LLM."""
        try:
            self.llm_manager.configure_default_llm()
        except ValueError as e:
            self.notify(str(e), severity="error")

    def get_current_llm_config(self):
        """Fetch the current LLM config from LLMManager."""
        return self.llm_manager.get_current_llm_config()

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(id="agent-centre", classes="dynamic-spacer"):
            yield LeftSideContainer(classes="left-dynamic-spacer")
            yield DynamicContainer(id="center-dynamic-container-clarity", classes="center-dynamic-spacer")

        with Vertical(id="app-layout"):
            with Collapsible(title="Task Panel", id="state-info-collapsible", collapsed=False):
                yield StateInfo(id="state-info")
                yield StateButtonGrid(self.state_machine, id="button-grid")
        
        yield Footer(id="footer", name="footer")


    def on_mount(self) -> None:
        logging.info("ClarityScreen on_mount called")
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



    def update_header(self, session_name=None, agent_name=None):
        if not session_name:
            session_name = self.session_manager.current_session_name
        if not agent_name:
            agent_name = self.agent_name_plain
        
        if session_name and agent_name:
            self.sub_title = f"Active Session: {session_name} - Current Agent: {agent_name}"
            logging.info(f"Updated app sub_title with session name: {session_name} and agent: {agent_name}")
        elif session_name:
            self.sub_title = f"Active Session: {session_name}"
            logging.info(f"Updated app sub_title with session name: {session_name}")
        elif agent_name:
            self.sub_title = f"Current Agent: {agent_name}"
            logging.info(f"Updated app sub_title with agent name: {agent_name}")
        else:
            self.sub_title = ""
            logging.info("Cleared app sub_title")
        
        # Force a refresh of the entire app
        self.refresh(layout=True)

    def clear_session(self):
        self.session_manager.current_session_data = None
        self.session_manager.current_session_name = None
        self.update_header()
        

    def update_ui_after_session_load(self):
        try:
            dynamic_container = self.query_one("#center-dynamic-container-clarity", DynamicContainer)
            dynamic_container.clear_content()

            stored_state = self.session_manager.get_data("current_state", screen_name=self.screen_name)
            if stored_state and stored_state in self.state_machine.states:
                self.state_machine.current_state = self.state_machine.states[stored_state]
            else:
                self.state_machine.current_state = self.state_machine.states["initial"]

            self.query_one(StateInfo).update_state_info(self.state_machine, "")
            self.query_one(StateButtonGrid).update_buttons()
        except NoMatches:
            logging.warning("Dynamic container not found; scheduling UI update later.")
            self.call_later(self.update_ui_after_session_load)



    def on_agent_selected(self, event: AgentSelected):
        self.current_agent = event.agent_name.plain
        self.agent_name_plain = event.agent_name.plain
        self.notify(f"Loaded Agent: {event.agent_name.plain}")
        # self.query_one(DynamicContainer).clear_content()
        dynamic_container = self.query_one("#center-dynamic-container-clarity", DynamicContainer)
        dynamic_container.clear_content()
        
        # Update header with current agent and session (if available)
        self.update_header(agent_name=event.agent_name.plain)
        
        # Store the current agent in the session data
        self.session_manager.update_data("current_agent", self.current_agent, screen_name=self.screen_name)

    def transition_to_agent_loaded(self) -> None:
        agent_loaded_state = self.state_machine.states.get("agent_loaded")
        if agent_loaded_state:
            self.state_machine.current_state = agent_loaded_state
            logging.info(f"Set state to agent_loaded")
            self.query_one(StateInfo).update_state_info(self.state_machine, "")
            self.query_one(StateButtonGrid).update_buttons()
            # Store the current state in the session (per-screen data)
            self.session_manager.update_data("current_state", "agent_loaded", screen_name=self.screen_name)
        else:
            logging.error(f"Failed to set state to agent_loaded: State not found")

    def transition_to_analyse_state(self) -> None:
        analyse_state = self.state_machine.states.get("analysis_ready")
        if analyse_state:
            self.state_machine.current_state = analyse_state
            logging.info(f"Set state to analysis_ready")
            self.query_one(StateInfo).update_state_info(self.state_machine, "")
            self.query_one(StateButtonGrid).update_buttons()
            
            # Store the current state in the session (per-screen data)
            self.session_manager.update_data("current_state", "analysis_ready", screen_name=self.screen_name)

        else:
            logging.error(f"Failed to set state to analysis_ready: State not found")

    def transition_to_analysis_ready(self) -> None:
        logging.info("Entering transition_to_analysis_ready method")
        
        if not self.session_manager.current_session_data:
            logging.error("No active session. Cannot transition to analysis_ready state.")
            self.notify("No active session. Please create or load a session first.", severity="error")
            return

        logging.info(f"Current session name: {self.session_manager.current_session_name}")
        logging.info(f"Current session data: {self.session_manager.current_session_data}")

        analysis_ready_state = self.state_machine.states.get("analysis_ready")
        if analysis_ready_state:
            self.state_machine.current_state = analysis_ready_state
            logging.info(f"Set state to analysis_ready")
            self.query_one(StateInfo).update_state_info(self.state_machine, "")
            self.query_one(StateButtonGrid).update_buttons()
            
            try:
                # Store the current state in the session (per-screen data)
                logging.info(f"Attempting to update session data. Screen name: {self.screen_name}")
                self.session_manager.update_data("current_state", "analysis_ready", screen_name=self.screen_name)
                logging.info("Successfully updated session data with new state")
            except Exception as e:
                logging.error(f"Failed to update session data: {str(e)}")
                logging.error(f"Exception type: {type(e)}")
                logging.error(f"Exception args: {e.args}")
                self.notify(f"Error updating session data: {str(e)}", severity="error")
        else:
            logging.error(f"Failed to set state to analysis_ready: State not found")
            self.notify("Failed to transition to analysis ready state", severity="error")

        logging.info("Exiting transition_to_analysis_ready method")


    @on(UIButtonPressed)
    def handle_ui_button_pressed(self, event: UIButtonPressed) -> None:
        logging.debug(f"Handler 'handle_ui_button_pressed' invoked with button_id: {event.button_id}")
        # dynamic_container = self.query_one(DynamicContainer)
        # dynamic_container.clear_content()
        dynamic_container = self.query_one("#center-dynamic-container-clarity", DynamicContainer)
        dynamic_container.clear_content()


        try:
            # Use the UI factory to get the corresponding UI and action
            ui_class, action = self.ui_factory.ui_factory(event.button_id)
            
            # Load the UI component if it exists (for "load-session")
            if ui_class:
                if event.button_id == "load-session" and not self.session_manager.list_sessions():
                    self.notify("No sessions available. Create a new session first.", severity="warning")
    
                else:
                    dynamic_container.load_content(ui_class())

            # Handle the action (state change) only if there's an action function
            if action:
                action()

        except ValueError as e:
            logging.error(f"Error: {e}")

    def on_action_selected(self, event: ActionSelected) -> None:
        if event.action == "reset":
            self.clear_session()

        # dynamic_container = self.query_one(DynamicContainer)
        # dynamic_container.clear_content()
        dynamic_container = self.query_one("#center-dynamic-container-clarity", DynamicContainer)
        dynamic_container.clear_content()



        if event.action == "system_message":
            # Load SystemMessageUI instead of just displaying a label
            dynamic_container.mount(SystemMessageUI())
        elif event.action == "load_agent":
            dynamic_container.mount(LoadAgentUI())
        elif event.action == "analyze":
            dynamic_container.mount(AnalyzeUI())
        elif event.action == "feedback_input":
            dynamic_container.mount(FeedbackInputUI())
        elif event.action == "feedback_output":
            dynamic_container.mount(FeedbackOutputUI())
        elif event.action == "feedback_rules":
            dynamic_container.mount(FeedbackRulesUI())
        elif event.action == "feedback_constraints":
            dynamic_container.mount(FeedbackConstraintsUI())
        else:
            # For other actions, load generic content as before
            dynamic_container.mount(CenterContent(event.action))
