
from typing import Dict, List, Set
from textual.app import App, ComposeResult
from textual.widgets import Button, Static, Label, Header, Footer
from textual.containers import Grid, Vertical, Horizontal, Container
from textual.widgets import Placeholder, Collapsible
from textual.message import Message

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
            print(f"Action '{action}' executed. New state: {self.state_machine.current_state.name}")
            self.post_message(ActionSelected(action))  # Emit custom event
        else:
            print(f"Action '{action}' is not allowed in current state: {self.state_machine.current_state.name}")

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
            yield Button("Load", id="load-button", classes="left-side-button")
            yield Button("List", id="list-button", classes="left-side-button")
            yield Button("Save", id="save-button", classes="left-side-button")

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
            yield Placeholder("center", id="center-placeholder", classes="center-dynamic-spacer")
            yield Placeholder("right", classes="right-dynamic-spacer")

        with Vertical(id="app-layout"):
            with Collapsible(title="State Information", id="state-info-collapsible"):
                yield StateInfo(id="state-info")
            yield StateButtonGrid(self.state_machine, id="button-grid")
      
        yield Footer(id="footer", name="footer")

    def on_mount(self) -> None:
        self.query_one(StateInfo).update_state_info(self.state_machine, "")

    def on_action_selected(self, event: ActionSelected) -> None:
        center_placeholder = self.query_one("#center-placeholder")
        center_placeholder.remove_children()
        center_placeholder.mount(CenterContent(event.action))

    def on_left_side_button_pressed(self, event: LeftSideButtonPressed) -> None:
        center_placeholder = self.query_one("#center-placeholder")
        center_placeholder.remove_children()
        
        if event.button_id == "load-button":
            # Directly set the state to agent_loaded
            agent_loaded_state = self.state_machine.states.get("agent_loaded")
            if agent_loaded_state:
                self.state_machine.current_state = agent_loaded_state
                print(f"Set state to agent_loaded")
                self.query_one(StateInfo).update_state_info(self.state_machine, "")
                self.query_one(StateButtonGrid).update_buttons()
            else:
                print(f"Failed to set state to agent_loaded: State not found")
            
        center_placeholder.mount(CenterContent(f"Left side button pressed: {event.button_id}"))


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