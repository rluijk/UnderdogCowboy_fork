from uccli import State, StateMachine


def create_agent_assessment_state_machine() -> StateMachine:
    # Define States
    initial_state = State("initial")
    agent_loaded_state = State("agent_loaded")
    analysis_ready_state = State("analysis_ready")
    category_selected_state = State("category_selected")
    prompt_generated_state = State("prompt_generated")

    # Define Transitions
    initial_state.add_transition("load_agent", agent_loaded_state)
    agent_loaded_state.add_transition("analyze", analysis_ready_state)
    agent_loaded_state.add_transition("generate_prompt", prompt_generated_state)

    analysis_ready_state.add_transition("analyze", analysis_ready_state)
    analysis_ready_state.add_transition("toggle_fixed", analysis_ready_state)
    analysis_ready_state.add_transition("list_categories", analysis_ready_state)
    analysis_ready_state.add_transition("select_category", category_selected_state)
    analysis_ready_state.add_transition("define_category", analysis_ready_state)

    analysis_ready_state.add_transition("generate_prompt", prompt_generated_state)

    category_selected_state.add_transition("define_category", analysis_ready_state)
    category_selected_state.add_transition("toggle_fixed", analysis_ready_state)

    # Add Reset Transitions
    for state in [initial_state, agent_loaded_state, analysis_ready_state, category_selected_state, prompt_generated_state]:
        state.add_transition("reset", initial_state)

    # Create State Machine
    state_machine = StateMachine(initial_state)
    for state in [agent_loaded_state, analysis_ready_state, category_selected_state, prompt_generated_state]:
        state_machine.add_state(state)

    return state_machine