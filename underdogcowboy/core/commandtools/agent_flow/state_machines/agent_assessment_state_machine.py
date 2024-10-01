from uccli import State, StateMachine

def create_agent_assessment_state_machine() -> StateMachine:
    """Create and return the state machine for agent assessment."""
    initial_state = State("start_assessment")
    assessment_in_progress_state = State("assessment_in_progress")
    assessment_completed_state = State("assessment_completed")

    # Define transitions for this state machine
    initial_state.add_transition("start", assessment_in_progress_state)
    assessment_in_progress_state.add_transition("complete", assessment_completed_state)

    # Create and return the state machine
    state_machine = StateMachine(initial_state)
    state_machine.add_state(assessment_in_progress_state)
    state_machine.add_state(assessment_completed_state)

    return state_machine
