from uccli import GenericCLI, StateMachine, State, command

"""if works, refactor in lib"""
import functools

def cancellable_command(prompt="Are you sure you want to proceed? (y/n): "):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(self, arg):
            confirm = input(prompt)
            if confirm.lower() != 'y':
                print("Operation cancelled.")
                return "CANCEL_TRANSITION"
            return func(self, arg)
        return wrapper
    return decorator

def visualize_after_command(visualize_func_name: str):
    def decorator(cmd_func):
        @functools.wraps(cmd_func)
        def wrapper(self, *args, **kwargs):
            result = cmd_func(self, *args, **kwargs)
            # Only visualize if the command didn't return "CANCEL_TRANSITION"
            if result != "CANCEL_TRANSITION":
                visualize_func = getattr(self, visualize_func_name)
                visualize_func(self.state_machine)
            return result
        return wrapper
    return decorator

"""if works, refactor the above lib, included the onecmd we override below"""


class AgentClarityProcessor(GenericCLI):
    def __init__(self):
        # Define states
        initial_state = State("initial")
        agent_created_state = State("agent_created")
        agent_loaded_state = State("agent_loaded")
        model_selected_state = State("model_selected")
        analysis_ready_state = State("analysis_ready")

        # Define transitions
        initial_state.add_transition("load_agent", agent_loaded_state)
        initial_state.add_transition("create_agent", agent_created_state)
        initial_state.add_transition("list_models", initial_state)

        agent_created_state.add_transition("load_agent", agent_loaded_state)

        agent_loaded_state.add_transition("load_agent", agent_loaded_state)
        agent_loaded_state.add_transition("select_model", model_selected_state)
        agent_loaded_state.add_transition("system_message", agent_loaded_state)
        agent_loaded_state.add_transition("list_models", agent_loaded_state)

        model_selected_state.add_transition("load_agent", agent_loaded_state)
        model_selected_state.add_transition("select_model", model_selected_state)
        model_selected_state.add_transition("analyze", analysis_ready_state)
        model_selected_state.add_transition("system_message", model_selected_state)

        analysis_ready_state.add_transition("load_agent", agent_loaded_state)
        analysis_ready_state.add_transition("select_model", model_selected_state)
        analysis_ready_state.add_transition("analyze", analysis_ready_state)
        analysis_ready_state.add_transition("export_analysis", analysis_ready_state)
        analysis_ready_state.add_transition("feedback", analysis_ready_state)
        analysis_ready_state.add_transition("feedback_input", analysis_ready_state)
        analysis_ready_state.add_transition("feedback_output", analysis_ready_state)
        analysis_ready_state.add_transition("feedback_rules", analysis_ready_state)
        analysis_ready_state.add_transition("feedback_constraints", analysis_ready_state)
        analysis_ready_state.add_transition("system_message", analysis_ready_state)

        # Add reset transition to all states
        for state in [agent_created_state, agent_loaded_state, model_selected_state, analysis_ready_state]:
            state.add_transition("reset", initial_state)

        # Create state machine
        state_machine = StateMachine(initial_state)
        for state in [agent_created_state, agent_loaded_state, model_selected_state, analysis_ready_state]:
            state_machine.add_state(state)

        super().__init__(state_machine)


    def onecmd(self, line):
        cmd, arg, line = self.parseline(line)
        if not line:
            return self.emptyline()
        if cmd is None:
            return self.default(line)
        self.lastcmd = line
        if cmd == '':
            return self.default(line)
        else:
            available_commands = self.get_available_commands()
            if cmd not in available_commands:
                print(f"Command '{cmd}' not available in current state.")
                return False
            
            # Execute the command
            try:
                func = getattr(self, 'do_' + cmd)
                result = func(arg)
                
                # Check if the command is a transition and the result is not "CANCEL_TRANSITION"
                if cmd in self.state_machine.current_state.transitions and result != "CANCEL_TRANSITION":
                    self.state_machine.transition(cmd)
                
                # Visualize after successful command execution and potential state transition
                if result != "CANCEL_TRANSITION" and hasattr(self, 'visualize_state_machine'):
                    self.visualize_state_machine(self.state_machine)
                
                return result if result != "CANCEL_TRANSITION" else False
            except AttributeError:
                return self.default(line)

    @command("print_state_machine", "Print the current state machine configuration")
    def do_print_state_machine(self, arg):
        print("State Machine Configuration:")
        for state in self.state_machine.states:
            print(f"\nState: {state.name}")
            for command, next_state in state.transitions.items():
                print(f"  {command} -> {next_state.name}")

    @command("load_agent", "Load an agent definition from a JSON file")
    def do_load_agent(self, arg):
        print("load_agent command executed")

    @command("create_agent", "Create a new agent definition")
    def do_create_agent(self, arg):
        print("create_agent command executed")

    @command("select_model", "Select a model to use")
    def do_select_model(self, arg):
        print("select_model command executed")

    @cancellable_command("Are you sure you want to proceed with the analysis? (y/n): ")
    @command("analyze", "Perform an initial analysis of the loaded agent definition")
    def do_analyze(self, arg):
        print("Starting analysis...")
        # Here you'd perform the actual analysis
        print("Analysis complete.")
        print("Available commands in this state: export_analysis, feedback, feedback_input, feedback_output, feedback_rules, feedback_constraints")
        # Return True to allow the state transition
        return True

    @command("export_analysis", "Export the last analysis to a markdown file")
    def do_export_analysis(self, arg):
        print("export_analysis command executed")

    @command("feedback", "Get general feedback on the agent definition")
    def do_feedback(self, arg):
        print("feedback command executed")

    @command("feedback_input", "Get feedback on the input handling of the agent definition")
    def do_feedback_input(self, arg):
        print("feedback_input command executed")

    @command("feedback_output", "Get feedback on the output generation of the agent definition")
    def do_feedback_output(self, arg):
        print("feedback_output command executed")

    @command("feedback_rules", "Get feedback on the rules of the agent definition")
    def do_feedback_rules(self, arg):
        print("feedback_rules command executed")

    @command("feedback_constraints", "Get feedback on the constraints of the agent definition")
    def do_feedback_constraints(self, arg):
        print("feedback_constraints command executed")

    @command("system_message", "Manage the system message for the currently loaded agent")
    def do_system_message(self, arg):
        print("system_message command executed")

    @command("list_models", "List all available LLM models")
    def do_list_models(self, arg):
        if self.state_machine.current_state.name in ["initial", "agent_loaded"]:
            print("list_models command executed")
        else:
            print("list_models is only available in the initial and agent_loaded states.")

    @command("reset", "Reset the process and return to the initial state")
    def do_reset(self, arg):
        print("Resetting to initial state")
        self.state_machine.current_state = self.state_machine.initial_state

    @command("exit", "Exit the Agent Clarity Tool")
    def do_exit(self, arg):
        print("Exiting Agent Clarity Tool. Goodbye!")
        return True

    def postcmd(self, stop, line):
        """Hook method executed just after a command dispatch is finished."""
        if not stop:
            print(f"\nCurrent state: {self.state_machine.current_state.name}")
            # You could add more state-specific information here
        return stop
    
def main():
    AgentClarityProcessor().cmdloop()

if __name__ == "__main__":
    main()