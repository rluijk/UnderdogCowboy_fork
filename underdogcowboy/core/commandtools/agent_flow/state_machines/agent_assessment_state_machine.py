from uccli import StateMachine
from .state_ui import UIState


def create_agent_assessment_state_machine() -> StateMachine:

    # Define States
    initial_state = UIState("initial")
    agent_loaded_state = UIState("agent_loaded")
    analysis_ready_state = UIState("analysis_ready")
    export_ready_state = UIState("export_ready")

    
    # Active buttons in initial state
    initial_state.add_transition("load_agent", agent_loaded_state)
    
    
    # Active buttons in agent loaded state
    agent_loaded_state.add_transition("analyze", analysis_ready_state)

    # Active buttons in analyze ready state
    analysis_ready_state.add_transition("export", export_ready_state)
    analysis_ready_state.add_transition("analyze", analysis_ready_state)

    # Active buttons in export ready state
    export_ready_state.add_transition("analyze",analysis_ready_state)
    export_ready_state.add_transition("load_agent", agent_loaded_state)
    export_ready_state.add_transition("export", export_ready_state)
    

    # Add Reset Transitions
    for state in [initial_state, agent_loaded_state, analysis_ready_state,export_ready_state]:
        state.add_transition("reset", initial_state)

    # Create State Machine
    state_machine = StateMachine(initial_state)
    for state in [agent_loaded_state,analysis_ready_state,export_ready_state]:
        state_machine.add_state(state)

    return state_machine