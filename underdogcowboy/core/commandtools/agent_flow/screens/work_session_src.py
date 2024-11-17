from typing import Dict, List, Set
import os
import logging

from textual import on
from textual.app import ComposeResult
from textual.containers import Vertical, Horizontal
from textual.widgets import  (  Header, Footer, Collapsible )
from textual.css.query import NoMatches

from uccli import StateMachine  
from underdogcowboy.core.config_manager import LLMConfigManager 

# Storage
from session_manager import SessionManager

# Configs
from llm_manager import LLMManager

# UI
from ui_factory import UIFactory
from ui_components.dynamic_container import DynamicContainer
from ui_components.state_button_grid_ui import StateButtonGrid 
from ui_components.state_info_ui import StateInfo
from ui_components.session_dependent import SessionDependentUI
from ui_components.center_content_ui import CenterContent

from ui_components.left_side_ui import LeftSideContainer
from ui_components.work_summary_ui import WorkSummaryUI

# Screens
from screens.session_screen import SessionScreen

# State Machines for each screen
from state_machines.work_sessions_state_machine import create_works_session_state_machine

# events
from events.action_events import ActionSelected
from events.button_events import UIButtonPressed

class WorkSessionScreen(SessionScreen):

    def __init__(self, 
                 state_machine: StateMachine = None, 
                 session_manager: SessionManager = None,
                 *args, **kwargs):
        
        super().__init__(*args, **kwargs)

        self.state_machine = state_machine or create_works_session_state_machine()
        self.session_manager = session_manager  
        self.ui_factory = UIFactory(self)
        
        self.current_agent = None
        self.agent_name_plain = None
        self.title = "Agent WorkSession"
        
        # Initialize LLMManager
        self.llm_manager = LLMManager(
            config_manager=LLMConfigManager(),
            default_provider='anthropic',
            default_model_id='claude-3-5-sonnet-20241022', 
            default_model_name='Claude 3.5 Sonnet (Upgrade)' 
        )
        
        # Set the default LLM during initialization
        self.llm_manager.set_default_llm()
            
        # Define the screen name for namespacing
        self.screen_name = "WorkSessionScreen"

        self._pending_session_manager = None

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(id="agent-centre", classes="dynamic-spacer"):
            yield LeftSideContainer(classes="left-dynamic-spacer agent-clarity-left")
            yield DynamicContainer(id="center-dynamic-container", classes="center-dynamic-spacer")        

        with Vertical(id="app-layout"):
            with Collapsible(title="Task Panel", id="state-info-collapsible", collapsed=False):                  
                yield StateInfo(id="state-info")
                yield StateButtonGrid(self.state_machine, id="button-grid", state_machine_active_on_mount=True)  
                
        yield Footer(id="footer", name="footer")

    def on_mount(self) -> None:
        state_info = self.query_one("#state-info", StateInfo)
        state_info.update_state_info(self.state_machine, "")
        self.update_header()

        # Apply pending session manager after widgets are ready
        if self._pending_session_manager:
            session_manager = self._pending_session_manager
            self._pending_session_manager = None
            self.call_later(self.set_session_manager, session_manager)

    def update_header(self, session_name=None, agent_name=None):
        self.refresh(layout=True)            

    @on(UIButtonPressed)
    def handle_ui_button_pressed(self, event: UIButtonPressed) -> None:
        logging.debug(f"Handler 'handle_ui_button_pressed' invoked with button_id: {event.button_id}")
        dynamic_container = self.query_one("#center-dynamic-container", DynamicContainer)
        dynamic_container.clear_content()

        try:
            # Use the UI factory to get the corresponding UI and action
            ui_class, action = self.ui_factory.ui_factory(event.button_id)

            # Load the UI component if it exists (for "load-session")
            if ui_class:
                if event.button_id == "load-session" and not self.session_manager.list_sessions():
                    self.notify("No sessions available. Create a new session first.", severity="warning")
                else:
                    # Check if ui_class is a subclass of SessionDependentUI
                    if issubclass(ui_class, SessionDependentUI):
                        ui_instance = ui_class(session_manager=self.session_manager, 
                                            screen_name=self.screen_name,
                                            agent_name_plain=self.agent_name_plain)
                    else:
                        ui_instance = ui_class()

                    dynamic_container.load_content(ui_instance)

            # Handle the action (state change) only if there's an action function
            if action:
                action()

        except ValueError as e:
            logging.error(f"Error: {e}")

    def on_action_selected(self, event: ActionSelected) -> None:
        action = event.action

        if action == "reset":
            # self.clear_session()
            self.state_machine.current_state = self.state_machine.states["initial"]
            self.app.query_one(StateInfo).update_state_info(self.state_machine, "")
            self.app.query_one(StateButtonGrid).update_buttons()


        dynamic_container = self.query_one("#center-dynamic-container", DynamicContainer)
        dynamic_container.clear_content()

        # Mapping actions to their respective UI classes
        ui_class = {
            "leftoff_summary": WorkSummaryUI,
        }.get(action)

        if ui_class:
            # Instantiate with parameters if it's a subclass of SessionDependentUI
            if issubclass(ui_class, SessionDependentUI):
                dynamic_container.mount(ui_class(
                    session_manager=self.session_manager,
                    screen_name=self.screen_name,
                    agent_name_plain=self.agent_name_plain
                ))
            else:
                dynamic_container.mount(ui_class())
        else:
            # For other actions, load generic content as before
            dynamic_container.mount(CenterContent(action))


    # Required for this subclass
    def update_ui_after_session_load(self):
        try:
            dynamic_container = self.query_one("#center-dynamic-container", DynamicContainer)
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
