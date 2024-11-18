
from uccli import StateMachine
from .state_ui import UIState


def create_clarity_state_machine() -> StateMachine:
    initial_state = UIState("initial")
    agent_loaded_state = UIState("agent_loaded")
    analysis_ready_state = UIState("analysis_ready")

    # Define transitions
    initial_state.add_transition("load_agent", agent_loaded_state)

    agent_loaded_state.add_transition("load_agent", agent_loaded_state)
    # agent_loaded_state.add_transition("system_message", agent_loaded_state)
    agent_loaded_state.add_transition("analyze", analysis_ready_state)  # Added transition
 
    analysis_ready_state.add_transition("analyze", analysis_ready_state)
    analysis_ready_state.add_transition("export_analysis", analysis_ready_state)
    
    analysis_ready_state.add_transition("feedback_input", analysis_ready_state)
    analysis_ready_state.add_transition("feedback_output", analysis_ready_state)
    analysis_ready_state.add_transition("feedback_rules", analysis_ready_state)
    analysis_ready_state.add_transition("feedback_constraints", analysis_ready_state)
    
    # analysis_ready_state.add_transition("system_message", analysis_ready_state)

    # Add reset transition to all states
    for state in [initial_state, agent_loaded_state, analysis_ready_state]:
        state.add_transition("reset", initial_state)

    # Create state machine
    state_machine = StateMachine(initial_state)
    for state in [agent_loaded_state, analysis_ready_state]:
        state_machine.add_state(state)

    return state_machine
