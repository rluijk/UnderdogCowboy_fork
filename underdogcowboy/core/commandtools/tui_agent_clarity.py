
from typing import Dict, List, Any 

from textual.app import App, ComposeResult
from textual.widgets import Button, Static, Header, Footer
from textual.reactive import reactive
from textual.containers import VerticalScroll, Container, Vertical, Horizontal

from agent_clarity_02 import AgentClarityProcessor

from uccli import StateMachine


def generate_state_button_mapping(state_machine: StateMachine) -> Dict[str, List[str]]:
    """
    Generate a mapping of states to their allowed actions (buttons) based on the state machine
     configuration.

    :param state_machine: The StateMachine object
    :return: A dictionary mapping state names to lists of allowed actions
    """
    state_button_mapping = {}

    for state_name in state_machine.states:
        state = state_machine.states[state_name]
        allowed_actions = list(state.transitions.keys())

        state_button_mapping[state_name] = allowed_actions

    return state_button_mapping

class AgentClarityApp(App):

    CSS = """
    .left-column, .right-column {
        width: 20%;
        height: 100%;
        background: green;
    }

    .main-area {
        width: 60%;
        background: $surface;
    }

    Footer {
        background: $accent;
        dock: bottom;
        height: 20%;  /* Increased height further for debugging */
        padding: 1 1;
    }

    .state-button {
        margin: 1 1;
        width: auto;
        height: 3rem;  /* Explicit height for buttons */
    }
    """

    BINDINGS = [("q", "quit", "Quit")]

    current_state = reactive("initial")

    def __init__(self, state_button_mapping):
        super().__init__()
        self.state_button_mapping = state_button_mapping
        self.buttons = {}

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)

        # Main content layout
        with Horizontal():
            yield Static("Left Column", classes="left-column")
            yield Static("Main Work Area", classes="main-area")
            yield Static("Right Column", classes="right-column")

        # Debug: Log button creation and layout
        print("Composing footer with buttons...")

        # Buttons docked in the footer
        with Footer():
            with Horizontal():
                for action in set(action for actions in self.state_button_mapping.values() for action in actions):
                    button = Button(action.replace("_", " ").title(), id=action, classes="state-button")
                    self.buttons[action] = button
                    print(f"Creating button: {action}")  # Debug: Print button creation
                    yield button

    def on_mount(self) -> None:
        self.update_button_states()
        print("App mounted!")  # Debug: Log when app is mounted

    def watch_current_state(self, new_state: str) -> None:
        self.update_button_states()

    def update_button_states(self) -> None:
        active_buttons = self.state_button_mapping.get(self.current_state, [])
        for action, button in self.buttons.items():
            button.disabled = action not in active_buttons

    def on_button_pressed(self, event: Button.Pressed) -> None:
        action = event.button.id
        print(f"Button pressed: {action}")  # Debug: Log button presses
        if action == "load_agent":
            self.current_state = "agent_loaded"
        elif action == "create_agent":
            self.current_state = "agent_created"
        elif action == "select_model":
            self.current_state = "model_selected"
        elif action == "analyze":
            self.current_state = "analysis_ready"
        elif action == "reset":
            self.current_state = "initial"

    def action_quit(self) -> None:
        self.exit()

# In your main script:
def main():
    
    state_machine = AgentClarityProcessor().state_machine
    # Generate the state_button_mapping                                                      
    state_button_mapping = generate_state_button_mapping(state_machine)            
                                                                                                
    # Print the mapping for verification                                                     
    print("State-Button Mapping:")                                                           
    for state, actions in state_button_mapping.items():                                 
        print(f"{state}: {actions}")        

    state_button_mapping = generate_state_button_mapping(state_machine)
    app = AgentClarityApp(state_button_mapping)
    app.run()

if __name__ == "__main__":
    main()