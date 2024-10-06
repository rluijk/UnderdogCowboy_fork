import logging
import yaml
from typing import Dict, Set

from textual import on
from textual.app import App
from textual.events import Event
from textual.reactive import Reactive

from underdogcowboy.core.config_manager import LLMConfigManager

""" imports clarity system """
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

# Configs
from llm_manager import LLMManager

# Custom events
from events.session_events import SessionSyncStopped

logging.basicConfig(
    filename='app_clarity-oct_2.log',
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Load configuration from YAML file
def load_config(config_path: str) -> dict:
    with open(config_path, 'r') as file:
        return yaml.safe_load(file)

class MultiScreenApp(App):
    """Main application managing multiple screens and session synchronization."""

    # Key bindings for user interactions to switch between screens or sync sessions
    BINDINGS = [
        ("t", "return_to_timeline", "TimeLine Editor"),
        ("c", "return_to_clarity", "Agent Clarity"),
        ("a", "return_to_agent_assessment_builder", "Agent Assessment Builder"),
        ("s", "sink_sessions", "Sink Sessions to Current Screen"),  # Key binding for synchronization
    ]

    # Reactive property to track if session synchronization is active
    sync_active: Reactive[bool] = Reactive(False)
    # Shared SessionManager that can be used across screens when syncing is active
    shared_session_manager: SessionManager = None

    def __init__(self, config_path: str, **kwargs):
        super().__init__(**kwargs)
        # Load configuration from the YAML file
        self.config = load_config(config_path)
        
        # Initialize the storage manager to manage persistent session data
        self.storage_manager: StorageInterface = JSONStorageManager(base_dir=self.config['storage']['base_dir'])
        # Dictionary to hold SessionManagers for each screen
        self.screen_session_managers: Dict[str, SessionManager] = {}
        # Set to hold all session-related screens
        self.session_screens: Set['SessionScreen'] = set()

        # Initialize LLMManager for managing language model configurations using loaded config
        self.llm_manager = LLMManager(
            config_manager=LLMConfigManager(),
            default_provider=self.config['llm']['default_provider'],
            default_model_id=self.config['llm']['default_model_id'],
            default_model_name=self.config['llm']['default_model_name']
        )
        
        # Set the default LLM during initialization
        self.llm_manager.set_default_llm()

    def on_mount(self) -> None:
        """Mount screens when the app starts."""
        # Initialize individual SessionManagers for each screen by default
        self.screen_session_managers = {
            "TimeLine Editor": SessionManager(self.storage_manager),
            "Clarity": SessionManager(self.storage_manager),
            "Agent Assessment Builder": SessionManager(self.storage_manager),
        }

        # Register each SessionManager to post messages to this app
        for session_manager in self.screen_session_managers.values():
            session_manager.set_message_post_target(self)  # Register with the app to post messages

        # Create screen instances with appropriate state machines and session managers
        timeline_editor_screen = TimeLineEditorScreen(
            state_machine=create_timeline_editor_state_machine(),
            session_manager=self.screen_session_managers["TimeLine Editor"]
        )
        clarity_screen = ClarityScreen(
            state_machine=create_clarity_state_machine(),
            session_manager=self.screen_session_managers["Clarity"]
        )
        agent_assessment_builder_screen = AgentAssessmentBuilderScreen(
            state_machine=create_agent_assessment_state_machine(),
            session_manager=self.screen_session_managers["Agent Assessment Builder"]
        )

        # Add session-related screens to the set for managing sessions easily
        self.session_screens.update({
            timeline_editor_screen,
            clarity_screen,
            agent_assessment_builder_screen,
        })

        # Install screens in the application with their respective names
        # The `install_screen` method is used to register each screen with the application. 
        # This makes it possible to switch to the specified screen by its name during runtime. 
        # The lambda function ensures that a new instance of the screen is created when needed.
        # We use `install_screen` this way because we are running async code using a combination 
        # of `asyncio` and `concurrent.futures.ThreadPoolExecutor`. This allows us to run 
        # processes in the background while keeping screens responsive and ensuring they come back in an activated state.
        self.install_screen(lambda: timeline_editor_screen, name="TimeLine Editor")
        self.install_screen(lambda: clarity_screen, name="Clarity")
        self.install_screen(lambda: agent_assessment_builder_screen, name="Agent Assessment Builder")
        
        # Start with the Clarity screen as the main app screen
        self.push_screen("Clarity")





    def get_current_llm_config(self):
        """Fetch the current LLM config from LLMManager."""
        return self.llm_manager.get_current_llm_config()


    @on(SessionSyncStopped)
    def on_session_sync_stopped(self, event: SessionSyncStopped) -> None:
        """Handle session synchronization stop triggered by any screen."""
        if not self.sync_active:
            return

        # Revert all screens to their individual SessionManagers
        for screen in self.session_screens:
            individual_session_manager = self.screen_session_managers.get(screen.screen_name)
            if individual_session_manager:
                screen.set_session_manager(individual_session_manager)
                # Do not call update_ui_after_session_load() directly to prevent unintended UI updates

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

        # Check if the active screen has a session loaded before proceeding
        if active_screen.session_manager.current_session_data is None:
            self.notify("No session loaded on the active screen. Cannot synchronize sessions.", severity="warning")
            return

        # Proceed with synchronization by sharing the active session manager across all screens
        active_session_manager = active_screen.session_manager
        self.shared_session_manager = active_session_manager

        # Set all other screens to use the shared session manager
        for screen in self.session_screens:
            if screen != active_screen:
                screen.set_session_manager(active_session_manager)
                # Do not call update_ui_after_session_load() directly to prevent unintended UI updates

        self.sync_active = True
        self.notify("Session synchronization enabled. All screens now share the active session. ", severity="info")
        logging.info("Session synchronization enabled.")

    def get_active_session_screen(self) -> 'SessionScreen':
        """Get the currently active session-related screen."""
        # Iterate over session_screens and find the one with is_current == True
        for screen in self.session_screens:
            if screen.is_current:
                return screen
        return None

def main():
    import os
    config_path = os.path.join(os.path.dirname(__file__), 'config.yaml')
    app = MultiScreenApp(config_path=config_path)
    app.run()

if __name__ == "__main__":
    main()