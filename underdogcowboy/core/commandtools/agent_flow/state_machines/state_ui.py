
from uccli import State

class UIState(State):
    def __init__(self, name: str):
        super().__init__(name)
        self.hidden_transitions = set()  # Store transitions that should be hidden in the UI

    def add_transition(self, action: str, next_state: 'State', hide_button: bool = False):
        super().add_transition(action, next_state)
        if hide_button:
            self.hidden_transitions.add(action)

    def get_visible_transitions(self) -> list[str]:
        """Returns transitions that are not hidden."""
        return [action for action in self.transitions if action not in self.hidden_transitions]
