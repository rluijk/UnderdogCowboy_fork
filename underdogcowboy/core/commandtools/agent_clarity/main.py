from typing import Dict, List, Set
import logging

from textual import on
from textual.app import App, ComposeResult
from textual.containers import Grid, Vertical, Horizontal, Container
from textual.message import Message
from textual.widgets import  (  Button, Static, Label, Header, Footer, Collapsible )

from uccli import StateMachine, State, StorageManager
from underdogcowboy.core.config_manager import LLMConfigManager 
from underdogcowboy.core.llm_response_markdown import LLMResponseRenderer

""" imports clarity sytem """
# utils
from agent_llm_handler import send_agent_data_to_llm

# UI
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
from ui_components.load_session_ui import LoadSessionUI

# Events
from events.button_events import UIButtonPressed
from events.agent_events import AgentSelected
from events.session_events import SessionSelected, NewSessionCreated
from events.action_events import ActionSelected


logging.basicConfig(
    filename='app_clarity.log', 
    level=logging.DEBUG, 
    format='%(asctime)s - %(levelname)s - %(message)s'
)


class MainApp(App):

    CSS_PATH = "state_machine_app.css"

    DEFAULT_PROVIDER = 'anthropic'  
    DEFAULT_MODEL_ID = 'claude-3-5-sonnet-20240620'
    DEFAULT_MODEL_NAME = 'Claude 3.5 Sonnet'

    def __init__(self, state_machine: StateMachine, storage_manager: StorageManager, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.state_machine = state_machine
        self.storage_manager = storage_manager
        self.current_storage = None
        self.current_agent= None
        self.agent_name_plain = None
        self.title = "Agent Clarity"  # Set an initial title for the app
        self.llm_config_manager = LLMConfigManager()
        self.set_default_llm()  # Set the default LLM during initialization

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(id="agent-centre", classes="dynamic-spacer"):
            yield LeftSideContainer(classes="left-dynamic-spacer")
            yield DynamicContainer(id="center-dynamic-container", classes="center-dynamic-spacer")

        with Vertical(id="app-layout"):
            with Collapsible(title="Task Panel", id="state-info-collapsible", collapsed=False):
                yield StateInfo(id="state-info")
                yield StateButtonGrid(self.state_machine, id="button-grid")
        
        yield Footer(id="footer", name="footer")

    def on_mount(self) -> None:
        logging.info("MainApp on_mount called")
        self.query_one(StateInfo).update_state_info(self.state_machine, "")
        self.update_header()  # Initialize the header

    def update_header(self, session_name=None, agent_name=None):
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

    def set_default_llm(self):
        # Check if the default model is available
        available_models = self.llm_config_manager.get_available_models()
        if f"{self.DEFAULT_PROVIDER}:{self.DEFAULT_MODEL_ID}" in available_models:
            self.llm_config_manager.update_model_property(self.DEFAULT_PROVIDER, 'selected_model', self.DEFAULT_MODEL_ID)
            logging.info(f"Default LLM set to {self.DEFAULT_MODEL_NAME} ({self.DEFAULT_MODEL_ID})")
        else:
            # If the default model is not available, prompt to configure it
            logging.warning(f"Default model {self.DEFAULT_MODEL_NAME} is not configured.")
            self.configure_default_llm()

    def configure_default_llm(self):
        logging.info(f"Configuring default LLM: {self.DEFAULT_MODEL_NAME}")
        try:
            # This will prompt for API key if not already configured
            self.llm_config_manager.get_credentials(self.DEFAULT_PROVIDER)
            # Set the selected model
            self.llm_config_manager.update_model_property(self.DEFAULT_PROVIDER, 'selected_model', self.DEFAULT_MODEL_ID)
            logging.info(f"Default LLM {self.DEFAULT_MODEL_NAME} configured successfully")
        except Exception as e:
            logging.error(f"Failed to configure default LLM: {str(e)}")
            # You might want to show a notification to the user here
            self.notify("Failed to configure default LLM. Please check your settings.", severity="error")

    def get_current_llm_config(self):
        try:
            return self.llm_config_manager.get_credentials(self.DEFAULT_PROVIDER)
        except Exception as e:
            logging.error(f"Failed to get current LLM config: {str(e)}")
            return None

    def on_session_selected(self, event: SessionSelected):
        try:
            self.current_storage = self.storage_manager.load_session(event.session_name)
            self.notify(f"Session '{event.session_name}' loaded successfully")
            self.query_one(DynamicContainer).clear_content()
            
            # Retrieve the stored state from the session
            stored_state = self.current_storage.get_data("current_state")
            if stored_state and stored_state in self.state_machine.states:
                self.state_machine.current_state = self.state_machine.states[stored_state]
            else:
                # If no stored state or invalid state, set to a default state
                # TODO this would be need to be set via the CLI config, since this is dependd on the specific CLI 
                self.state_machine.current_state = self.state_machine.states["analysis_ready"]
            
            # Use existing method to update UI
            self.query_one(StateInfo).update_state_info(self.state_machine, "")
            self.query_one(StateButtonGrid).update_buttons()
            
            

            logging.info(f"Attempting to update header with session name: {event.session_name}")           
            self.update_header(session_name=event.session_name, agent_name=self.agent_name_plain)

            self.log_header_state()  # Log the header state after update
                        

        except ValueError as e:
            logging.error(f"Error loading session: {str(e)}")
            self.notify(f"Error loading session: {str(e)}", severity="error")

    def on_agent_selected(self, event: AgentSelected):
        self.current_agent = AgentSelected
        self.agent_name_plain = event.agent_name.plain
        self.notify(f"Loaded Agent: {event.agent_name.plain}")
        self.query_one(DynamicContainer).clear_content()


         # Check if a session is loaded, if not, pass None for session_name
        session_name = None
        if self.current_storage:
            session_name = self.current_storage.get_data("session_name")

        # Update header with current agent and session (if available)
        self.update_header(session_name=session_name, agent_name=event.agent_name.plain)

    def ui_factory(self, button_id: str):
        ui_class, action = self.get_ui_and_action(button_id)
        return ui_class, action

    def get_ui_and_action(self, button_id: str):
        # Map button ID to UI class and action function
        if button_id == "load-session":
            ui_class_name = "LoadSessionUI"
            action_func_name = None
        elif button_id == "new-button":
            ui_class_name = "NewSessionUI"
            action_func_name = None
        elif button_id == "system-message":  # Handling system message button
            ui_class_name = "SystemMessageUI"
            action_func_name = None    
        elif button_id == "confirm-session-load":
            ui_class_name = None
            action_func_name = "transition_to_analysis_ready"
        else:
            raise ValueError(f"Unknown button ID: {button_id}. Hint: Ensure that this button ID is mapped correctly in 'get_ui_and_action'.")

        logging.info(f"Resolving UI class: {ui_class_name}, Action function: {action_func_name}")

        # Get the UI class and action function
        ui_class = globals().get(ui_class_name) if ui_class_name else None
        action_func = getattr(self, action_func_name, None) if action_func_name else None

        if not action_func and not ui_class:
            raise ValueError(f"No UI or action found for button ID: {button_id}")

        return ui_class, action_func

    def transition_to_agent_loaded(self) -> None:
        agent_loaded_state = self.state_machine.states.get("agent_loaded")
        if agent_loaded_state:
            self.state_machine.current_state = agent_loaded_state
            logging.info(f"Set state to agent_loaded")
            self.query_one(StateInfo).update_state_info(self.state_machine, "")
            self.query_one(StateButtonGrid).update_buttons()
        else:
            logging.error(f"Failed to set state to agent_loaded: State not found")
    def transition_to_analyse_state(self) -> None:
        analyse_state = self.state_machine.states.get("analysis_ready")
        if analyse_state:
            self.state_machine.current_state = analyse_state
            logging.info(f"Set state to analysis_ready")
            self.query_one(StateInfo).update_state_info(self.state_machine, "")
            self.query_one(StateButtonGrid).update_buttons()
        else:
            logging.error(f"Failed to set state to analysis_ready: State not found")
    def transition_to_analysis_ready(self) -> None:
        analysis_ready_state = self.state_machine.states.get("analysis_ready")
        if analysis_ready_state:
            self.state_machine.current_state = analysis_ready_state
            logging.info(f"Set state to analysis_ready")
            self.query_one(StateInfo).update_state_info(self.state_machine, "")
            self.query_one(StateButtonGrid).update_buttons()
            
            # Store the current state in the session
            if self.current_storage:
                self.storage_manager.save_current_session(self.current_storage)
        else:
            logging.error(f"Failed to set state to analysis_ready: State not found")

    def clear_session(self):
        self.current_storage = None
        self.update_header()
        self.log_header_state()  # Log the header state after clearing

    def on_new_session_created(self, event: NewSessionCreated):
        try:
            self.current_storage = self.storage_manager.create_session(event.session_name)
            self.notify(f"New session '{event.session_name}' created successfully")
            self.query_one(DynamicContainer).clear_content()
            self.transition_to_analysis_ready()
            
            logging.info(f"Attempting to update header with new session name: {event.session_name}")
            self.update_header(event.session_name)
            self.log_header_state()  # Log the header state after update
        except ValueError as e:
            logging.error(f"Error creating session: {str(e)}")
            self.notify(f"Error creating session: {str(e)}", severity="error")

    @on(UIButtonPressed)
    def handle_ui_button_pressed(self, event: UIButtonPressed) -> None:
        logging.debug(f"Handler 'handle_ui_button_pressed' invoked with button_id: {event.button_id}")
        dynamic_container = self.query_one(DynamicContainer)
        dynamic_container.clear_content()

        try:
            # Use the UI factory to get the corresponding UI and action
            ui_class, action = self.ui_factory(event.button_id)
            
            # Load the UI component if it exists (for "load-session")
            if ui_class:
                if event.button_id == "load-session" and not self.storage_manager.list_sessions():
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

        dynamic_container = self.query_one(DynamicContainer)
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

def create_state_machine() -> StateMachine:
    # Define states
    initial_state = State("initial")
    agent_loaded_state = State("agent_loaded")
    analysis_ready_state = State("analysis_ready")

    # Define transitions
    initial_state.add_transition("load_agent", agent_loaded_state)

    agent_loaded_state.add_transition("load_agent", agent_loaded_state)
    agent_loaded_state.add_transition("system_message", agent_loaded_state)
    agent_loaded_state.add_transition("analyze", analysis_ready_state)  # Added transition

    
    analysis_ready_state.add_transition("load_agent", agent_loaded_state)
    analysis_ready_state.add_transition("analyze", analysis_ready_state)
    analysis_ready_state.add_transition("export_analysis", analysis_ready_state)
    
    analysis_ready_state.add_transition("feedback_input", analysis_ready_state)
    analysis_ready_state.add_transition("feedback_output", analysis_ready_state)
    analysis_ready_state.add_transition("feedback_rules", analysis_ready_state)
    analysis_ready_state.add_transition("feedback_constraints", analysis_ready_state)
    
    analysis_ready_state.add_transition("system_message", analysis_ready_state)

    # Add reset transition to all states
    for state in [initial_state, agent_loaded_state, analysis_ready_state]:
        state.add_transition("reset", initial_state)

    # Create state machine
    state_machine = StateMachine(initial_state)
    for state in [agent_loaded_state, analysis_ready_state]:
        state_machine.add_state(state)

    return state_machine

def main():
    state_machine = create_state_machine()  # Initialize state machine first
    storage_manager = StorageManager("~/.tui_agent_clarity_03")
    
    # Now create the app, but don't pass the app reference to the state machine yet
    app = MainApp(state_machine, storage_manager)
    
    # Inject the app reference into the state machine after initialization
    state_machine.app = app
    
    # Run the app
    app.run()

if __name__ == "__main__":
    main()    