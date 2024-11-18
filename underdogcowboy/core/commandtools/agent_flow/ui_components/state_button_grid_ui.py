import logging
from typing import List

from textual import on
from textual.app import ComposeResult
from textual.widgets import Static, Button
from textual.containers import Grid
from uccli import StateMachine
from state_machines.state_ui import UIState

# UI
from ui_components.state_info_ui import StateInfo

# Events
from events.action_events import ActionSelected
from events.session_events import SessionStateChanged


class StateButtonGrid(Static):
    def __init__(self, state_machine: StateMachine, *args, state_machine_active_on_mount=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.state_machine = state_machine
        self.all_actions = self.get_ordered_actions()
        self.state_machine_active_on_mount = state_machine_active_on_mount

    def get_ordered_actions(self) -> List[str]:
        all_actions = set()
        for state in self.state_machine.states.values():
            if isinstance(state, UIState):
                all_actions.update(state.get_visible_transitions())  # Only include visible transitions
            else:
                all_actions.update(state.transitions.keys())  # Fallback in case of base State

        ordered_actions = []
        visited_states = set()
        state_queue = [self.state_machine.current_state]

        while state_queue:
            current_state = state_queue.pop(0)
            if current_state.name in visited_states:
                continue
            visited_states.add(current_state.name)

            if isinstance(current_state, UIState):
                state_actions = list(current_state.get_visible_transitions())  # Only consider visible actions
            else:
                state_actions = list(current_state.transitions.keys())  # Fallback in case of base State

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
        """Disable or update buttons based on state_machine_active_on_mount flag."""
        self.disable_buttons_initially()

    def disable_buttons_initially(self) -> None:
        """Disable all buttons initially unless the state machine is active."""
        if not self.state_machine_active_on_mount:
            for button in self.query("Button"):
                button.disabled = True
        else:
            self.update_buttons() 

    def on_button_pressed(self, event: Button.Pressed) -> None:
        action = str(event.button.label)
        self.post_message(ActionSelected(action))
 
        
    def update_buttons(self) -> None:
        """Update the buttons based on allowed actions from the state machine."""
        allowed_actions = self.state_machine.get_available_commands()
        for button in self.query("Button"):
            action = str(button.label)
            button.disabled = action not in allowed_actions

    @on(SessionStateChanged)
    def on_session_state_changed(self, event: SessionStateChanged) -> None:
        """Enable or disable all buttons based on session state."""
        if event.session_active:
            # Enable buttons based on state machine logic
            self.update_buttons()
        else:
            # No active session, disable all buttons
            for button in self.query("Button"):
                button.disabled = True
