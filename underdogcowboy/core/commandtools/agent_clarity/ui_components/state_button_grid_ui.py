import logging
from typing import List

from textual.app import ComposeResult
from textual.widgets import Static, Button
from textual.containers import Grid
from uccli import StateMachine

""" Clarity System """
# UI
from ui_components.state_info_ui import StateInfo

# Events
from events.action_events import ActionSelected

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
