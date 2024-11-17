from uccli import StateMachine
from .state_ui import UIState

def create_timeline_editor_state_machine() -> StateMachine:
    # Define states
    initial_state = UIState("initial")
    agent_loaded_state = UIState("agent_loaded")
    dialog_loaded_state = UIState("dialog_loaded")

    # Define transitions for each state
    # Initial state transitions
    initial_state.add_transition("new_agent", agent_loaded_state)  # Start a new agent conversation
    initial_state.add_transition("new_dialog", dialog_loaded_state)  # Start a new dialog conversation
    initial_state.add_transition("load_agent", agent_loaded_state)  # Load existing agent
    initial_state.add_transition("load_dialog", dialog_loaded_state)  # Load existing dialog

    # Agent loaded state transitions
    agent_loaded_state.add_transition("load_agent", agent_loaded_state)  # Reload agent
    agent_loaded_state.add_transition("save_agent", agent_loaded_state)  # Save agent
    agent_loaded_state.add_transition("reset", initial_state)  # Reset to initial state

    # Dialog loaded state transitions
    dialog_loaded_state.add_transition("load_dialog", dialog_loaded_state)  # Reload dialog
    dialog_loaded_state.add_transition("save_dialog", dialog_loaded_state)  # Save dialog
    dialog_loaded_state.add_transition("reset", initial_state)  # Reset to initial state
    
    # Ensure reset transition is available in all states
    for state in [initial_state, agent_loaded_state, dialog_loaded_state]:
        state.add_transition("reset", initial_state)

    # Create the state machine and add states
    state_machine = StateMachine(initial_state)
    for state in [initial_state, agent_loaded_state, dialog_loaded_state]:
        state_machine.add_state(state)

    return state_machine
