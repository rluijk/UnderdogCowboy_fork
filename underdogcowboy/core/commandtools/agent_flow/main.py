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


from textual.app import ComposeResult
from textual.containers import Vertical, Horizontal
from textual.widgets import Header, Footer, Collapsible

from ui_components.left_side_ui import LeftSideContainer
from ui_components.dynamic_container import DynamicContainer

from ui_components.state_button_grid_ui import StateButtonGrid
from ui_components.state_info_ui import StateInfo

# dynamic for json config of the UI
from underdogcowboy.ui_components_registry import get_ui_component



def generate_compose(dynamic_container_id="center-dynamic-container", screen_type=None):
    """
    Generate a basic compose method for a screen.

    Parameters:
    - dynamic_container_id (str): ID for the DynamicContainer, defined in JSON.
    - screen_type (str): Screen type (e.g., "session_based").

    Returns:
    - A dynamically generated compose method.
    """
    def compose(self) -> ComposeResult:
        # Header
        yield Header()

        # Horizontal layout with optional LeftSideContainer
        if screen_type == "session_based":
            with Horizontal(id="agent-centre", classes="dynamic-spacer"):
                yield LeftSideContainer(classes="left-dynamic-spacer")
                yield DynamicContainer(id=dynamic_container_id, classes="center-dynamic-spacer")
        else:
            with Horizontal(id="agent-centre", classes="dynamic-spacer"):
                yield DynamicContainer(id=dynamic_container_id, classes="center-dynamic-spacer")

        # Task Panel
        with Vertical(id="app-layout"):
            with Collapsible(title="Task Panel", id="state-info-collapsible", collapsed=False):
                yield StateInfo(id="state-info")
                yield StateButtonGrid(self.state_machine, id="button-grid", state_machine_active_on_mount=True)

        # Footer
        yield Footer(id="footer", name="footer")

    return compose

def generate_on_mount(screen_name, dynamic_container_component=None, dynamic_container_id=None):
    def on_mount(self):
        logging.info(f"{screen_name} on_mount called")

        # Update state info and header
        state_info = self.query_one("#state-info", StateInfo)
        state_info.update_state_info(self.state_machine, "")
        self.update_header()

        # Handle pending session manager
        if self._pending_session_manager:
            session_manager = self._pending_session_manager
            self._pending_session_manager = None
            self.call_later(self.set_session_manager, session_manager)

        # Defer mounting the dynamic container component
        if dynamic_container_component and dynamic_container_id:
            def mount_component():
                try:
                    container = self.query_one(f"#{dynamic_container_id}")
                    component_class = get_ui_component(dynamic_container_component)
                    if container and component_class:
                        container.mount(component_class())
                        logging.info(f"Component {dynamic_container_component} mounted in {dynamic_container_id}")
                    else:
                        logging.warning(f"Failed to mount {dynamic_container_component} in {dynamic_container_id}")
                except Exception as e:
                    logging.error(f"Error during component mounting: {e}")

            self.call_later(mount_component)

    return on_mount




class MultiScreenApp(App):
    """Main application managing multiple screens and session synchronization."""

    # CSS_PATH = "./state_machine_app_candidate.tcss"
    CSS_PATH = "./v02_octa_state_machine_app_candidate.tcss"
    ENABLE_COMMAND_PALETTE = False

    # Key bindings for user interactions to switch between screens or sync sessions
    BINDINGS = []
    
    # Reactive property to track if session synchronization is active
    # sync_active: Reactive[bool] = Reactive(False)
    
    # Shared SessionManager that can be used across screens when syncing is active
    shared_session_manager: SessionManager = None

    def __init__(self, config_path: str, **kwargs): 
        super().__init__(**kwargs)
        # Load configuration from the YAML file
        self.config = load_config(config_path)
        self.screen_map = {}  

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

        self.sync_active: Reactive[bool] = Reactive(False)
        # Ensure no unintended triggers:
        if self.sync_active:
            return
        self.sync_active = True

    def install_screen(self, factory, name: str) -> None:
        """Register a screen factory in screen_map."""
        if name in self.screen_map:
            logging.warning(f"Screen '{name}' is already installed.")
            return
        self.screen_map[name] = factory  # Register factory
        super().install_screen(factory, name=name)

    def push_screen(self, screen_name: str) -> None:
        """Push a screen if it is registered."""
        if screen_name not in self.screen_map:
            logging.error(f"Screen '{screen_name}' not found in screen_map.")
            return
        if self.screen and self.screen.name == screen_name:
            logging.debug(f"Screen '{screen_name}' is already active.")
            return
        super().push_screen(screen_name)

    def on_mount(self) -> None:
        """Mount screens when the app starts, dynamically from configuration."""

        self._initialize_bindings_from_config()

        # Load and merge configurations
        current_dir = os.path.dirname(__file__)
        default_config_path = os.path.join(current_dir, "screen_config.json")
        user_config_path = os.path.expanduser("~/.underdogcowboy/screens/user_defined_screens.json")

        try:
            with open(default_config_path) as default_file, open(user_config_path) as user_file:
                screen_configs = json.load(default_file)
                screen_configs.update(json.load(user_file))
        except FileNotFoundError:
            raise FileNotFoundError("Screen configuration file(s) not found.")
        except json.JSONDecodeError as e:
            logging.error(f"Invalid JSON in screen configuration: {e}")
            return

        # Register each screen
        for screen_name, config in screen_configs.items():
            if screen_name in ("initial_screen", "global_bindings") or screen_name.startswith("_"):
                continue

            # Initialize SessionManager
            session_manager = SessionManager(self.storage_manager)
            session_manager.set_message_post_target(self)
            self.screen_session_managers[screen_name] = session_manager

            # Retrieve screen and state machine details
            state_machine_func = globals().get(config["state_machine"])
            if state_machine_func is None:
                raise ValueError(f"State machine function '{config['state_machine']}' not found.")

            screen_class = globals().get(config["screen_class"])
            if screen_class is None:
                raise ValueError(f"Screen class '{config['screen_class']}' not found.")

            # Extract dynamic container configuration
            dynamic_container_config = config.get("dynamic_container", {})
            dynamic_container_id = dynamic_container_config.get("id", "center-dynamic-container")
            dynamic_container_component = dynamic_container_config.get("component")

            # Generate and attach the compose method
            compose_method = generate_compose(
                dynamic_container_id=dynamic_container_id,
                screen_type=config.get("screen_type", None)
            )
            setattr(screen_class, "compose", compose_method)

            # Generate and attach the on_mount method
            on_mount_method = generate_on_mount(
                screen_name=screen_name,
                dynamic_container_component=dynamic_container_component,
                dynamic_container_id=dynamic_container_id
            )
            setattr(screen_class, "on_mount", on_mount_method)

            # Define screen factory
            def screen_factory(sc, sm, sm_func):
                def factory():
                    return sc(state_machine=sm_func(), session_manager=sm)
                return factory

            # Install the screen
            self.install_screen(screen_factory(screen_class, session_manager, state_machine_func), name=screen_name)

        # Set the initial screen
        initial_screen = screen_configs.get("initial_screen")
        if initial_screen:
            self.push_screen(initial_screen)
        else:
            logging.warning("No initial_screen defined in configuration.")



    def _initialize_bindings_from_config(self) -> None:
        """Initialize bindings from configuration at startup."""
        current_dir = os.path.dirname(__file__)
        default_config_path = os.path.join(current_dir, "screen_config.json")
        user_config_path = os.path.expanduser("~/.underdogcowboy/screens/user_defined_screens.json")

        # Load default configuration
        try:
            with open(default_config_path) as default_file:
                screen_configs = json.load(default_file)
        except FileNotFoundError:
            raise FileNotFoundError(f"Configuration file not found at {default_config_path}")

        # Load user-defined configuration and merge if it exists
        if os.path.exists(user_config_path):
            try:
                with open(user_config_path) as user_file:
                    user_configs = json.load(user_file)
                    screen_configs.update(user_configs)
            except json.JSONDecodeError as e:
                logging.error(f"Failed to parse user-defined screens file: {e}")

        # Set up bindings from the merged configuration
        for screen_name, screen_data in screen_configs.items():
            # Skip non-dictionary entries like "initial_screen"
            if not isinstance(screen_data, dict):
                continue

            if screen_name.startswith("_") or screen_name in ("initial_screen", "global_bindings"):
                logging.info(f"Skipping disabled screen: {screen_name}")
                continue

            bindings = screen_data.get("bindings", [])
            for binding in bindings:
                action_name = binding["action"]
                self.bind(
                    binding["key"],                  # Pass keys as a positional argument
                    action=action_name,
                    description=binding["description"]
                )

                # Dynamically create the action method for each binding
                action_method = self.create_action_method(screen_name)
                action_method_name = f"action_{action_name}"
                action_method.__name__ = action_method_name

                # Check if the method already exists to avoid overwriting
                if not hasattr(MultiScreenApp, action_method_name):
                    setattr(MultiScreenApp, action_method_name, action_method)
                    logging.info(f"Created action method: {action_method_name} for screen: {screen_name}")
                else:
                    logging.warning(f"Action method {action_method_name} already exists. Skipping creation.")


    def create_action_method(self, screen_name):
        def action_method(*args, **kwargs):  # Accept any arguments
            if self.screen and self.screen.name != screen_name:
                self.switch_screen(screen_name)
        return action_method


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
    