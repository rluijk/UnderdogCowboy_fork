from uccli import StateMachine
from .state_ui import UIState


def create_timeline_editor_state_machine() -> StateMachine:
    """Create and return the state machine for the timeline editor."""
    initial_state = UIState("initial")
    editing_in_progress_state = UIState("editing_in_progress")
    editing_completed_state = UIState("editing_completed")

    # Define transitions for this state machine
    initial_state.add_transition("edit", editing_in_progress_state)
    editing_in_progress_state.add_transition("complete", editing_completed_state)

    # Create and return the state machine
    state_machine = StateMachine(initial_state)
    state_machine.add_state(editing_in_progress_state)
    state_machine.add_state(editing_completed_state)

    return state_machine
