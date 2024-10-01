

import logging

from textual import on
from textual.app import ComposeResult   
from textual.screen import Screen
from textual.containers import Vertical, Horizontal
from textual.widgets import  (  Label, Header, Footer, Collapsible )

from uccli import StateMachine, StorageManager

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
from ui_components.load_session_ui import LoadSessionUI
from ui_components.new_session_ui import NewSessionUI

# Events
from events.button_events import UIButtonPressed
from events.agent_events import AgentSelected
from events.session_events import SessionSelected, NewSessionCreated
from events.action_events import ActionSelected

# State Machines for each screen
from state_machines.agent_assessment_state_machine import create_agent_assessment_state_machine
from state_machines.clarity_state_machine import create_clarity_state_machine
from state_machines.timeline_editor_state_machine import create_timeline_editor_state_machine

""" imports clarity sytem """
# utils
from agent_llm_handler import send_agent_data_to_llm

# Storage
from session_manager import SessionManager

# Configs
from llm_manager import LLMManager

class TimeLineEditorScreen(Screen):
    """A screen for the timeline editor."""
    

    def __init__(self, storage_manager: StorageManager, state_machine: StateMachine = None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.title = "Timeline Editor"
        self.state_machine = state_machine or create_timeline_editor_state_machine()
        self.session_manager = SessionManager(storage_manager)  # Pass storage manager
        self.storage_manager = storage_manager

        self.ui_factory = UIFactory(self) 

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
        logging.info("TimeLineEditorScreen on_mount called")
        # Ensure the `StateInfo` widget exists before querying it
        state_info = self.query_one("#state-info")
        state_info.update_state_info(self.state_machine, "")
        self.update_header()     


    def update_header(self, session_name=None, agent_name=None):
        self.sub_title = "Timeline Editor"
        self.refresh(layout=True)

    @on(UIButtonPressed)
    def handle_ui_button_pressed(self, event: UIButtonPressed) -> None:
        logging.debug(f"Handler 'handle_ui_button_pressed' invoked with button_id: {event.button_id}")
        dynamic_container = self.query_one(DynamicContainer)
        dynamic_container.clear_content()

        try:
            # Use the UI factory to get the corresponding UI and action
            ui_class, action = self.ui_factory.ui_factory(event.button_id)
            
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