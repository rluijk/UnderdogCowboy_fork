# main_app.py

import logging
from typing import Dict, Set

from textual import on
from textual.app import App
from textual.events import Event
from textual.reactive import Reactive

from state_management.json_storage_manager import JSONStorageManager
from state_management.storage_interface import StorageInterface

# State Machines for each screen
from state_machines.agent_assessment_state_machine import create_agent_assessment_state_machine
from state_machines.clarity_state_machine import create_clarity_state_machine
from state_machines.timeline_editor_state_machine import create_timeline_editor_state_machine

# Screens
from screens.agent_assessment_builder_scr import AgentAssessmentBuilderScreen
from screens.timeline_editor_src import TimeLineEditorScreen    
from screens.agent_clarity_src import ClarityScreen

# Session Initializer
from session_initializer import initialize_shared_session_manager

from session_manager import SessionManager

# Custom events
from events.session_events import SessionSyncStopped

logging.basicConfig(
    filename='app_clarity-oct_2.log', 
    level=logging.DEBUG, 
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class MultiScreenApp(App):
    """Main application managing multiple screens and session synchronization."""

    BINDINGS = [
        ("t", "return_to_timeline", "TimeLine Editor"), 
        ("c", "return_to_clarity", "Agent Clarity"),
        ("a", "return_to_agent_assessment_builder", "Agent Assessment Builder"),
        ("s", "sink_sessions", "Sink Sessions to Current Screen"),  # Key binding for synchronization
    ]

    sync_active: Reactive[bool] = Reactive(False)
    shared_session_manager: SessionManager = None  # Shared SessionManager

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.storage_manager: StorageInterface = JSONStorageManager(base_dir="~/.tui_agent_clarity_03")
        self.screen_session_managers: Dict[str, SessionManager] = {}
        self.session_screens: Set['SessionScreen'] = set()

    def on_mount(self) -> None:
        """Mount screens when the app starts."""
        # Initialize individual SessionManagers for each screen by default
        self.screen_session_managers = {
            "TimeLine Editor": SessionManager(self.storage_manager),
            "Clarity": SessionManager(self.storage_manager),
            "Agent Assessment Builder": SessionManager(self.storage_manager),
        }

        # Create screen instances
        timeline_editor_screen = TimeLineEditorScreen(
            storage_interface=self.storage_manager, 
            state_machine=create_timeline_editor_state_machine(),
            session_manager=self.screen_session_managers["TimeLine Editor"]
        )
        clarity_screen = ClarityScreen(
            storage_interface=self.storage_manager, 
            state_machine=create_clarity_state_machine(), 
            session_manager=self.screen_session_managers["Clarity"]
        )
        agent_assessment_builder_screen = AgentAssessmentBuilderScreen(
            storage_interface=self.storage_manager, 
            state_machine=create_agent_assessment_state_machine(), 
            session_manager=self.screen_session_managers["Agent Assessment Builder"]
        )

        # Add session-related screens to the set
        self.session_screens.update({
            timeline_editor_screen,
            clarity_screen,
            agent_assessment_builder_screen,
        })

        # Install screens
        self.install_screen(lambda: timeline_editor_screen, name="TimeLine Editor")
        self.install_screen(lambda: clarity_screen, name="Clarity")
        self.install_screen(lambda: agent_assessment_builder_screen, name="Agent Assessment Builder")
        
        # Start with the main app screen
        self.push_screen("Clarity")

    @on(SessionSyncStopped)
    def on_session_sync_stopped(self, event: SessionSyncStopped) -> None:
        """Handle session synchronization stop triggered by any screen."""
        if not self.sync_active:
            return

        triggering_screen = event.screen
        screen_name = triggering_screen.screen_name  

        # Revert the triggering screen to its own SessionManager
        individual_session_manager = self.screen_session_managers.get(screen_name)
        if individual_session_manager:
            triggering_screen.set_session_manager(individual_session_manager)
            triggering_screen.update_ui_after_session_load()
            logging.info(f"Session synchronization stopped due to session change in {screen_name}.")
            self.notify(f"Session synchronization stopped due to session change in {screen_name}.", severity="info")
        
        # Disable synchronization entirely
        self.shared_session_manager = None
        self.sync_active = False
        logging.info("Session synchronization is now disabled.")
        self.notify("Session synchronization is now disabled.", severity="info")

    def action_return_to_clarity(self) -> None:
        """Action to return to the Clarity screen."""
        self.push_screen("Clarity")

    def action_return_to_timeline(self) -> None:
        """Action to navigate to the Timeline Editor screen."""
        self.push_screen("TimeLine Editor")

    def action_return_to_agent_assessment_builder(self) -> None:
        """Action to navigate to the Agent Assessment Builder screen."""
        self.push_screen("Agent Assessment Builder")

    def action_sink_sessions(self) -> None:
        """Sink all sessions to the currently active screen's SessionManager."""
        if self.sync_active:
            self.notify("Sessions are already synchronized.", severity="info")
            return

        # Find the active session screen
        active_screen = self.get_active_session_screen()
        if not active_screen:
            self.notify("No active session screen to sink sessions from.", severity="warning")
            return

        # Get the shared SessionManager from the active screen
        active_session_manager = active_screen.session_manager
        self.shared_session_manager = active_session_manager

        # Assign the shared SessionManager to all session-related screens
        for screen in self.session_screens:
            if screen != active_screen:
                screen.set_session_manager(active_session_manager)
                # Remove the direct call to update_ui_after_session_load()
                # screen.update_ui_after_session_load()

        self.sync_active = True
        self.notify("Session synchronization enabled. All screens now share the active session.", severity="info")
        logging.info("Session synchronization enabled.")


    def get_active_session_screen(self) -> 'SessionScreen':
        """Get the currently active session-related screen."""
        # Iterate over session_screens and find the one with is_current == True
        for screen in self.session_screens:
            if screen.is_current:
                return screen
        return None

def main():
    """Initialize and run the multi-screen app."""
    app = MultiScreenApp()
    app.run()

if __name__ == "__main__":
    main()
