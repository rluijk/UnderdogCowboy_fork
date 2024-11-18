
from uccli import StateMachine
from .state_ui import UIState


def create_works_session_state_machine() -> StateMachine:
    initial_state = UIState("initial")
    files_processed_state = UIState("files_processed")

    # Define transitions
    initial_state.add_transition("leftoff_summary", files_processed_state)

    # Add reset transition to all states
    for state in [initial_state, files_processed_state]:
        state.add_transition("reset", initial_state)

    # Create state machine
    state_machine = StateMachine(initial_state)
    for state in [files_processed_state]:
        state_machine.add_state(state)

    return state_machine
