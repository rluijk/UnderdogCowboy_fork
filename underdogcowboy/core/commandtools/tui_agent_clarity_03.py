from typing import Dict, List, Set
from textual.app import App, ComposeResult
from textual.widgets import Button, Static, Label, Header, Footer
from textual.containers import Grid, Vertical, Horizontal, Container
from textual.widgets import Placeholder, Collapsible
from textual.message import Message
import logging

from uccli import StateMachine, State  # Import from your library
#
#  Clear existing handlers and set up logging to a file
for handler in logging.root.handlers[:]:
    logging.root.removeHandler(handler)

logging.basicConfig(
    filename='app_03.log', 
    level=logging.DEBUG, 
    format='%(asctime)s - %(levelname)s - %(message)s'
)


class DynamicContainer(Static):
    """A container to dynamically load UI elements."""
    def clear_content(self):
        """Clear all current content."""
        self.remove_children()

    def load_content(self, widget: Static):
        """Load a new widget into the container."""
        self.mount(widget)

class LoadSessionUI(Static):
    """A simple UI that is loaded dynamically upon clicking 'Load'."""
    def compose(self) -> ComposeResult:
        yield Button("Confirm Session", id="internal_confirm_button")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "internal_confirm_button":
            # Post the correct button ID that triggers confirmation
            self.parent.post_message(LeftSideButtonPressed("confirm-session-load"))



class LoadUI(Static):
    """A simple UI that is loaded dynamically upon clicking 'Load'."""
    def compose(self) -> ComposeResult:
        yield Button("Confirm Load", id="confirm-load-button")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "confirm-load-button":
            # Do what the current load button does (change state)
            self.parent.post_message(LeftSideButtonPressed("confirm-load"))

class NewUI(Static):
    def compose(self) -> ComposeResult:
        yield Button("Confirm Analyze", id="confirm-analyze-button")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "confirm-analyze-button":
            self.parent.post_message(LeftSideButtonPressed("confirm-analyze"))

class StateInfo(Static):
    def compose(self) -> ComposeResult:
        yield Label("Current State:", id="state-label")
        yield Label("", id="current-state")
        yield Label("Available Actions:", id="actions-label")
        yield Label("", id="available-actions")
        yield Label("Current Action:", id="action-label")
        yield Label("", id="current-action")
     
    def update_state_info(self, state_machine: StateMachine, current_action: str = ""):
        self.query_one("#current-state").update(state_machine.current_state.name)
        self.query_one("#current-action").update(current_action)
        available_actions = ", ".join(state_machine.get_available_commands())
        self.query_one("#available-actions").update(available_actions)

class ActionSelected(Message):
    def __init__(self, action: str):
        self.action = action
        super().__init__()

class StateButtonGrid(Static):
    def __init__(self, state_machine: StateMachine, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.state_machine = state_machine
        self.all_actions = self.get_ordered_actions()

    def get_ordered_actions(self) -> List[str]:
        all_actions = set()
        for state in self.state_machine.states.values():
            all_actions.update(state.transitions.keys())

        ordered_actions = []
        visited_states = set()
        state_queue = [self.state_machine.current_state]

        while state_queue:
            current_state = state_queue.pop(0)
            if current_state.name in visited_states:
                continue
            visited_states.add(current_state.name)

            state_actions = list(current_state.transitions.keys())
            ordered_actions.extend([action for action in state_actions if action not in ordered_actions])

            for action, next_state in current_state.transitions.items():
                if next_state.name not in visited_states:
                    state_queue.append(next_state)

        ordered_actions.extend([action for action in all_actions if action not in ordered_actions])

        return ordered_actions

    def compose(self) -> ComposeResult:
        with Grid(id="button-grid"):
            for action in self.all_actions:
                yield Button(str(action), id=f"btn-{action}", classes="action-button")

    def on_mount(self) -> None:
        self.update_buttons()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        action = str(event.button.label)
        if self.state_machine.transition(action):
            logging.info(f"Action '{action}' executed. New state: {self.state_machine.current_state.name}")
            self.post_message(ActionSelected(action))  # Emit custom event
        else:
            logging.warning(f"Action '{action}' is not allowed in current state: {self.state_machine.current_state.name}")

        self.update_buttons()
        self.parent.query_one(StateInfo).update_state_info(self.state_machine, action)

    def update_buttons(self) -> None:
        allowed_actions = self.state_machine.get_available_commands()
        for button in self.query("Button"):
            action = str(button.label)
            button.disabled = action not in allowed_actions

class CenterContent(Static):
    def __init__(self, action: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.action = action

    def compose(self) -> ComposeResult:
        yield Label(f"Content for action: {self.action}")

class LeftSideButtonPressed(Message):
    def __init__(self, button_id: str):
        self.button_id = button_id
        super().__init__()

class LeftSideButtons(Container):
    def compose(self) -> ComposeResult:
        with Grid(id="left-side-buttons", classes="left-side-buttons"):
            yield Button("New", id="new-button", classes="left-side-button")
            # yield Button("Load", id="load-button", classes="left-side-button")
            yield Button("Load", id="load-session", classes="left-side-button")
            yield Button("List", id="list-button", classes="left-side-button")
            yield Button("Save", id="save-button", classes="left-side-button")
            yield Button("Config", id="config-button", classes="left-side-button")
            yield Button("Model", id="model-button", classes="left-side-button")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.post_message(LeftSideButtonPressed(event.button.id))

class LeftSideContainer(Container):
    def compose(self) -> ComposeResult:
        yield LeftSideButtons()

class MainApp(App):
    CSS_PATH = "state_machine_app.css"
            
    def __init__(self, state_machine: StateMachine, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.state_machine = state_machine

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(id="agent-centre", classes="dynamic-spacer"):
            yield LeftSideContainer(classes="left-dynamic-spacer")
            yield DynamicContainer(id="center-dynamic-container", classes="center-dynamic-spacer")
            yield Placeholder("right", classes="right-dynamic-spacer")

        with Vertical(id="app-layout"):
            with Collapsible(title="State Information", id="state-info-collapsible"):
                yield StateInfo(id="state-info")
            yield StateButtonGrid(self.state_machine, id="button-grid")
        
        yield Footer(id="footer", name="footer")

    def on_mount(self) -> None:
        self.query_one(StateInfo).update_state_info(self.state_machine, "")

    # Automated UI and action mapping
    def ui_factory(self, button_id: str):
        ui_class, action = self.get_ui_and_action(button_id)
        return ui_class, action

    def get_ui_and_action(self, button_id: str):
        # Map button ID to UI class and action function
        if button_id == "load-session":  # Only load the UI, no state change
            ui_class_name = "LoadSessionUI"
            action_func_name = None  # No action for just loading the UI
        elif button_id == "new-button":
            ui_class_name = "NewUI"
            action_func_name = "transition_to_analyse_state"
        elif button_id == "confirm-session-load":  # For confirmation, change state
            ui_class_name = None  # No UI to load
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
        else:
            logging.error(f"Failed to set state to analysis_ready: State not found")


    def on_left_side_button_pressed(self, event: LeftSideButtonPressed) -> None:
        dynamic_container = self.query_one(DynamicContainer)
        dynamic_container.clear_content()

        try:
            # Use the UI factory to get the corresponding UI and action
            ui_class, action = self.ui_factory(event.button_id)
            
            # Load the UI component if it exists (for "load-session")
            if ui_class:
                dynamic_container.load_content(ui_class())

            # Handle the action (state change) only if there's an action function
            if action:
                action()

        except ValueError as e:
            logging.error(f"Error: {e}")



    def on_action_selected(self, event: ActionSelected) -> None:
        dynamic_container = self.query_one(DynamicContainer)
        dynamic_container.clear_content()
        dynamic_container.mount(CenterContent(event.action))

def create_state_machine() -> StateMachine:
    # Define states
    initial_state = State("initial")
    agent_created_state = State("agent_created")
    agent_loaded_state = State("agent_loaded")
    model_selected_state = State("model_selected")
    analysis_ready_state = State("analysis_ready")

    # Define transitions
    agent_loaded_state.add_transition("system_message", agent_loaded_state)
    agent_loaded_state.add_transition("list_models", agent_loaded_state)

    model_selected_state.add_transition("analyze", analysis_ready_state)
    model_selected_state.add_transition("system_message", model_selected_state)

    analysis_ready_state.add_transition("analyze", analysis_ready_state)
    analysis_ready_state.add_transition("export_analysis", analysis_ready_state)
    analysis_ready_state.add_transition("feedback", analysis_ready_state)
    analysis_ready_state.add_transition("system_message", analysis_ready_state)

    # Add reset transition to all states
    for state in [agent_created_state, agent_loaded_state, model_selected_state, analysis_ready_state]:
        state.add_transition("reset", initial_state)

    # Create state machine
    state_machine = StateMachine(initial_state)
    for state in [agent_created_state, agent_loaded_state, model_selected_state, analysis_ready_state]:
        state_machine.add_state(state)

    return state_machine

def main():
    state_machine = create_state_machine()
    app = MainApp(state_machine)
    app.run()

if __name__ == "__main__":
    main()
