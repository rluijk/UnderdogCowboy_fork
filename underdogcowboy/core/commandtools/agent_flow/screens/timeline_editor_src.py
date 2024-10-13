import logging

from textual import on
from textual.app import ComposeResult
from textual.screen import Screen
from textual.containers import Vertical, Horizontal
from textual.widgets import Label, Header, Footer, Collapsible
from textual.css.query import NoMatches

from uccli import StateMachine

# Storage Interface and SessionManager
from session_manager import SessionManager

# UI Components
from ui_factory import UIFactory
from ui_components.dynamic_container import DynamicContainer
from ui_components.state_button_grid_ui import StateButtonGrid
from ui_components.state_info_ui import StateInfo
from ui_components.center_content_ui import CenterContent

# from ui_components.left_side_ui import LeftSideContainer

from ui_components.load_agent_ui import LoadAgentUI
from ui_components.load_dialog_ui  import LoadDialogUI

# Events
from events.button_events import UIButtonPressed
from events.agent_events import AgentSelected
from events.dialog_events import DialogSelected
from events.action_events import ActionSelected

# Screens
from screens.session_screen import SessionScreen

# State Machines
from state_machines.timeline_editor_state_machine import create_timeline_editor_state_machine

""""
Under development, the use and none use of SessionScreen.
SessionScreen

"""

class TimeLineEditorScreen(SessionScreen):
    """A screen for the timeline editor."""

    # CSS_PATH = "../state_machine_app.css"

    def __init__(self,
                 state_machine: StateMachine = None,
                 session_manager: SessionManager = None,
                 *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.title = "Timeline Editor"
        self.state_machine = state_machine or create_timeline_editor_state_machine()
        self.session_manager = session_manager
        self.ui_factory = UIFactory(self)
        self.screen_name = "TimeLineEditorScreen"
        self._pending_session_manager = None

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


    def update_header(self, session_name=None, agent_name=None):
        if not session_name:
            session_name = self.session_manager.current_session_name
        if not agent_name:
            agent_name = "Timeline Editor"
        self.sub_title = f"{agent_name}"
        if session_name:
            self.sub_title += f" - Active Session: {session_name}"
        self.refresh(layout=True)

    @on(UIButtonPressed)
    def handle_ui_button_pressed(self, event: UIButtonPressed) -> None:
        logging.debug(f"Handler 'handle_ui_button_pressed' invoked with button_id: {event.button_id}")
        dynamic_container = self.query_one("#center-dynamic-container-timeline-editor", DynamicContainer)
        dynamic_container.clear_content()

        try:
            # Use the UI factory to get the corresponding UI and action
            ui_class, action = self.ui_factory.ui_factory(event.button_id)

            # Load the UI component if it exists (for "load-session")
            if ui_class:
                if event.button_id == "load-session" and not self.session_manager.list_sessions():
                    self.notify("No sessions available. Create a new session first.", severity="warning")
                else:
                    ui_instance = ui_class()
                    dynamic_container.load_content(ui_instance)

            # Handle the action (state change) only if there's an action function
            if action:
                action()

        except ValueError as e:
            logging.error(f"Error: {e}")
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


    def transition_to_initial_state(self):
        initial_state = self.state_machine.states.get("initial")
        if initial_state:
            self.state_machine.current_state = initial_state
            logging.info(f"Set state to initial")
            self.query_one(StateInfo).update_state_info(self.state_machine, "")
            self.query_one(StateButtonGrid).update_buttons()
            # Store the current state in the session data
            self.session_manager.update_data("current_state", "initial", screen_name=self.screen_name)
        else:
            logging.error(f"Failed to set state to initial_state: State not found")


    def on_agent_selected(self, event: AgentSelected):
        self.current_agent = event.agent_name.plain
        self.agent_name_plain = event.agent_name.plain
        self.notify(f"Loaded Agent: {event.agent_name.plain}")
        dynamic_container = self.query_one("#center-dynamic-container-timeline-editor", DynamicContainer)
        dynamic_container.clear_content()
        
        # Update header with current agent and session (if available)
        self.update_header(agent_name=event.agent_name.plain)
        
        # Store the current agent in the session data
        # self.session_manager.update_data("current_agent", self.current_agent, screen_name=self.screen_name)

        # Here we can load the dialog from the json in the chat interface


    def on_action_selected(self, event: ActionSelected) -> None:
        action = event.action

        #if action == "reset":
            #self.clear_session()

        dynamic_container = self.query_one("#center-dynamic-container-timeline-editor", DynamicContainer)
        dynamic_container.clear_content()

        # Mapping actions to their respective UI classes
        ui_class = {
            "load_agent": LoadAgentUI,
            "load_dialog": LoadDialogUI,
        }.get(action)

        if ui_class:
            dynamic_container.mount(ui_class())
        else:
            # For other actions, load generic content as before
            dynamic_container.mount(CenterContent(action))

