from typing import Dict, List, Set
from textual.app import App, ComposeResult
from textual.widgets import Button, Static, Label
from textual.containers import Grid, Vertical
from uccli import StateMachine, State  # Import from your library

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

class StateButtonGrid(Static):
    def __init__(self, state_machine: StateMachine, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.state_machine = state_machine
        self.all_actions = self.get_all_actions()

    def get_all_actions(self) -> Set[str]:
        return set(action for state in self.state_machine.states.values() for action in state.transitions.keys())

    def compose(self) -> ComposeResult:
        with Grid(id="button-grid"):
            for action in self.all_actions:
                yield Button(str(action), id=f"btn-{action}", classes="action-button")

    def on_mount(self) -> None:
        self.update_buttons()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        action = str(event.button.label)
        if self.state_machine.transition(action):
            print(f"Action '{action}' executed. New state: {self.state_machine.current_state.name}")
        else:
            print(f"Action '{action}' is not allowed in current state: {self.state_machine.current_state.name}")

        self.update_buttons()
        self.parent.query_one(StateInfo).update_state_info(self.state_machine, action)

    def update_buttons(self) -> None:
        allowed_actions = self.state_machine.get_available_commands()
        for button in self.query("Button"):
            action = str(button.label)
            button.disabled = action not in allowed_actions

class StateMachineApp(App):
    CSS_PATH = "state_machine_app.css"

    def __init__(self, state_machine: StateMachine, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.state_machine = state_machine

    def compose(self) -> ComposeResult:
        with Vertical():
            yield StateInfo(id="state-info")
            yield StateButtonGrid(self.state_machine)

    def on_mount(self) -> None:
        self.query_one(StateInfo).update_state_info(self.state_machine, "")

def create_state_machine() -> StateMachine:
    # Define states
    initial_state = State("initial")
    agent_created_state = State("agent_created")
    agent_loaded_state = State("agent_loaded")
    model_selected_state = State("model_selected")
    analysis_ready_state = State("analysis_ready")

    # Define transitions
    initial_state.add_transition("load_agent", agent_loaded_state)
    initial_state.add_transition("create_agent", agent_created_state)
    initial_state.add_transition("list_models", initial_state)

    agent_created_state.add_transition("load_agent", agent_loaded_state)

    agent_loaded_state.add_transition("load_agent", agent_loaded_state)
    agent_loaded_state.add_transition("select_model", model_selected_state)
    agent_loaded_state.add_transition("system_message", agent_loaded_state)
    agent_loaded_state.add_transition("list_models", agent_loaded_state)

    model_selected_state.add_transition("load_agent", agent_loaded_state)
    model_selected_state.add_transition("select_model", model_selected_state)
    model_selected_state.add_transition("analyze", analysis_ready_state)
    model_selected_state.add_transition("system_message", model_selected_state)

    analysis_ready_state.add_transition("load_agent", agent_loaded_state)
    analysis_ready_state.add_transition("select_model", model_selected_state)
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
    app = StateMachineApp(state_machine)
    app.run()

if __name__ == "__main__":
    main()