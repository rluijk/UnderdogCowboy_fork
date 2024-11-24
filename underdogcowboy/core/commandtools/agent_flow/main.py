import logging
import yaml
import json
import sys
import os

# quick fix. The work, make relative imports with the "from .[folder] etc"
sys.path.append(os.path.dirname(os.path.abspath(__file__)))


from typing import Dict, Set, Union

from textual import on
from textual.app import App
from textual.events import Event
from textual.reactive import Reactive
from textual.binding import Binding
from dotenv import load_dotenv



from underdogcowboy.core.config_manager import LLMConfigManager

""" imports clarity system """
from state_management.json_storage_manager import JSONStorageManager
from state_management.storage_interface import StorageInterface

# State Machines for each screen
from state_machines.agent_assessment_state_machine import create_agent_assessment_state_machine
from state_machines.clarity_state_machine import create_clarity_state_machine
from state_machines.timeline_editor_state_machine import create_timeline_editor_state_machine
from underdogcowboy.core.commandtools.agent_flow.state_machines.work_sessions_state_machine import create_works_session_state_machine

# Screens
from screens.agent_assessment_builder_scr import AgentAssessmentBuilderScreen
from screens.timeline_editor_src import TimeLineEditorScreen    
from screens.agent_clarity_src import ClarityScreen
from screens.work_session_src import WorkSessionScreen

# Session Initializer
from session_manager import SessionManager

# Configs
from llm_manager import LLMManager

# Custom events
from events.session_events import SessionSyncStopped
from events.agent_events import AgentLoaded
from events.dialog_events import DialogLoaded

from copy_paste import ClipBoardCopy

# uc
from underdogcowboy.core.timeline_editor import CommandProcessor


class MultiScreenApp(App):
    """Main application managing multiple screens and session synchronization."""

    # CSS_PATH = "./state_machine_app_candidate.tcss"
    CSS_PATH = "./v02_octa_state_machine_app_candidate.tcss"
    ENABLE_COMMAND_PALETTE = False

    # Key bindings for user interactions to switch between screens or sync sessions
    BINDINGS = []
    
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
        # Set copy and paste 
        self.clipboard_content = ClipBoardCopy()
        self.clipboard_content.set_message_post_target(self)

        self.clarity_processor = None

    def on_mount(self) -> None:
        """Mount screens when the app starts, dynamically from configuration."""
        
        self._initialize_bindings_from_config()

        current_dir = os.path.dirname(__file__)
        config_path = os.path.join(current_dir, "screen_config.json")
        
        try:
            with open(config_path) as config_file:
                screen_configs = json.load(config_file)
        except FileNotFoundError:
            raise FileNotFoundError(f"Configuration file not found at {config_path}")
            
        self.screen_session_managers = {}
        self.session_screens = set()
        
        for screen_name, config in screen_configs.items():

            # the "_" for screens in development, or we do not want active during run time. 
            if screen_name.startswith("_") or screen_name in ("initial_screen", "global_bindings"):
                logging.info(f"Skipping disabled screen: {screen_name}")
                continue
                    

            session_manager = SessionManager(self.storage_manager)
            session_manager.set_message_post_target(self)
            self.screen_session_managers[screen_name] = session_manager
            
            state_machine_func = globals().get(config["state_machine"])
            if state_machine_func is None:
                raise ValueError(f"State machine function '{config['state_machine']}' not found.")
            
            screen_class = globals().get(config["screen_class"])
            if screen_class is None:
                raise ValueError(f"Screen class '{config['screen_class']}' not found.")
            
            screen_instance = screen_class(
                state_machine=state_machine_func(),
                session_manager=session_manager
            )
            
            self.session_screens.add(screen_instance)
            # Use a default argument in the lambda to capture the current screen_instance
            self.install_screen(lambda screen=screen_instance: screen, name=screen_name)

        # Set the initial screen dynamically from configuration
        self.push_screen(screen_configs["initial_screen"])

    def _initialize_bindings_from_config(self) -> None:
        """Initialize bindings from configuration at startup."""
        current_dir = os.path.dirname(__file__)
        config_path = os.path.join(current_dir, "screen_config.json")
        
        try:
            with open(config_path) as config_file:
                screen_configs = json.load(config_file)
        except FileNotFoundError:
            raise FileNotFoundError(f"Configuration file not found at {config_path}")
        


        # Set up bindings from configuration file
        for screen_name, screen_data in screen_configs.items():
            # Skip non-dictionary entries like "initial_screen"
            if not isinstance(screen_data, dict):
                continue

            if screen_name.startswith("_") or screen_name in ("initial_screen", "global_bindings"):
                logging.info(f"Skipping disabled screen: {screen_name}")
                continue
        
            bindings = screen_data.get("bindings", [])
            for binding in bindings:
                self.bind(
                    binding["key"],                  # Pass keys as a positional argument
                    action=binding["action"],
                    description=binding["description"]
                )

            # Dynamically create the action method
            action_name = binding["action"]
            action_method = self.create_action_method(screen_name)
            action_method_name = f"action_{action_name}"
            action_method.__name__ = action_method_name
            setattr(MultiScreenApp, action_method_name, action_method)
            logging.info(f"Created action method: {action_method_name} for screen: {screen_name}")

    def create_action_method(self,screen_name):
        def action_method(self):
            self.push_screen(screen_name)
        return action_method

    def __bck_on_mount(self) -> None:
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

    """ no longer needed, keep for some more testing of our screen_config.json config solution
    def action_return_to_clarity(self) -> None:
        self.push_screen("Clarity")

    def action_return_to_timeline(self) -> None:
        self.push_screen("TimeLine Editor")

    def action_return_to_agent_assessment_builder(self) -> None:
        self.push_screen("Agent Assessment Builder")
    """

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

def setup_logging(config):
    """Setup logging based on the environment variable."""
    # Load environment variables from .env file
    load_dotenv()

    if os.getenv("LOGGING_ENABLED") != "1":
        logging.disable(logging.CRITICAL)  # Disable all logging if not enabled
        return

    log_filename = config['logging']['filename']
    log_filepath = os.path.abspath(log_filename)

    # Clear existing handlers
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)

    logging.basicConfig(
        filename=log_filepath,
        level=config['logging']['level'],
        format=config['logging']['format']
    )
    print(f"Logging initialized. Log file: {log_filepath}")

def load_config(config_path: str) -> dict:
    with open(config_path, 'r') as file:
        return yaml.safe_load(file)

def main():
    config_path = os.path.join(os.path.dirname(__file__), 'config.yaml')
    config = load_config(config_path)
    setup_logging(config)

    # initial check for default model to have the API Key, if not ask for it.
    # should also take care of insert in json.
    config = load_config(config_path)
    default_provider = config['llm']['default_provider']
    config_manager = LLMConfigManager()
    config_manager.get_credentials(default_provider)
          


    print("Starting the app...")
    app = MultiScreenApp(config_path=config_path)
    app.run()

if __name__ == "__main__":
    main()
    