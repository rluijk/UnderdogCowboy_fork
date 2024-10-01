import logging
from typing import Dict, List, Set

from textual import on
from textual.app import App, ComposeResult

from uccli import  StorageManager

""" imports clarity sytem """
# State Machines for each screen
from state_machines.agent_assessment_state_machine import create_agent_assessment_state_machine
from state_machines.clarity_state_machine import create_clarity_state_machine
from state_machines.timeline_editor_state_machine import create_timeline_editor_state_machine

# Screens
from screens.agent_assessment_builder_scr import AgentAssessmentBuilderScreen
from screens.timeline_editor_src import TimeLineEditorScreen    
from screens.agent_clarity_src import ClarityScreen

logging.basicConfig(
    filename='app_clarity.log', 
    level=logging.DEBUG, 
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class MultiScreenApp(App):

    BINDINGS = [
        ("c", "return_to_clarity", "Agent Clarity"),
        ("t", "return_to_timeline", "TimeLine Editor"), 
        ("a", "return_to_agent_assessment_builder", "Agent Assessment Builder"),
    ]

    def on_mount(self) -> None:
        """Mount screens when the app starts."""
        # Initialize the shared storage manager
        self.storage_manager = StorageManager("~/.tui_agent_clarity_03")

        # Register each screen with its own StateMachine, while sharing the StorageManager
        self.install_screen(lambda: ClarityScreen(self.storage_manager, create_clarity_state_machine()), name="Clarity")
        self.install_screen(lambda: TimeLineEditorScreen(self.storage_manager, create_timeline_editor_state_machine()), name="TimeLine Editor")
        self.install_screen(lambda: AgentAssessmentBuilderScreen(self.storage_manager, create_agent_assessment_state_machine()), name="Agent Assessment Builder")
        
        # Start with the main app screen
        self.push_screen("Clarity")

    def action_return_to_clarity(self) -> None:
        """Action to return to the Clarity screen."""
        self.push_screen("Clarity")

    def action_return_to_timeline(self) -> None:
        """Action to navigate to the Timeline Editor screen."""
        self.push_screen("TimeLine Editor")

    def action_return_to_agent_assessment_builder(self) -> None:
        """Action to navigate to the Agent Assessment Builder screen."""
        self.push_screen("Agent Assessment Builder")

def main():
    # Initialize the multi-screen app (no need for state machine here if it's managed by a screen)
    app = MultiScreenApp()
    # Run the app
    app.run()

if __name__ == "__main__":
    main()    