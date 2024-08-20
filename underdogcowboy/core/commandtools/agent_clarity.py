import cmd
import json
from underdogcowboy.core.config_manager import LLMConfigManager
from underdogcowboy import AgentDialogManager, agent_clarity

class AgentClarityProcessor(cmd.Cmd):
    intro = "Welcome to the Agent Clarity Tool. Type 'help' or '?' to list commands."
    prompt = "(agent_clarity) "

    def __init__(self):
        super().__init__()
        self.config_manager = LLMConfigManager()
        self.current_model = None
        self.available_models = self.config_manager.get_available_models()
        self.current_agent_file = None
        self.agent_data = None

    def do_list_models(self, arg):
        """List all available LLM models."""
        print("Available models:")
        for i, model in enumerate(self.available_models, 1):
            print(f"  {i}. {model}")
        print("\nTo select a model, use 'select_model <number>' or 'select_model <name>'")

    def do_select_model(self, arg):
        """Select a model to use. Usage: select_model <number or name>"""
        if not arg:
            print("Please provide a model number or name. Use 'list_models' to see available options.")
            return

        if arg.isdigit():
            index = int(arg) - 1
            if 0 <= index < len(self.available_models):
                self.current_model = self.available_models[index]
            else:
                print(f"Invalid model number. Please choose between 1 and {len(self.available_models)}.")
                return
        else:
            if arg in self.available_models:
                self.current_model = arg
            else:
                print(f"Model '{arg}' not found. Use 'list_models' to see available options.")
                return

        print(f"Selected model: {self.current_model}")
        self.prompt = f"(agent_clarity:{self.current_model}) "

    def do_load_agent(self, arg):
        """Load an agent definition from a JSON file. Usage: load_agent <file_path>"""
        if not arg:
            print("Please provide a file path.")
            return

        try:
            with open(arg, 'r') as f:
                self.agent_data = json.load(f)
            self.current_agent_file = arg
            print(f"Agent definition loaded from {arg}")
        except FileNotFoundError:
            print(f"File not found: {arg}")
        except json.JSONDecodeError:
            print(f"Invalid JSON in file: {arg}")

    def do_analyze(self, arg):
        """Perform an initial analysis of the loaded agent definition."""
        if not self.current_model:
            print("No model selected. Please use 'select_model' first.")
            return
        if not self.agent_data:
            print("No agent definition loaded. Please use 'load_agent' first.")
            return

        provider, model = self.current_model.split(":")
        adm = AgentDialogManager([agent_clarity], model_name=model)
        response = agent_clarity >> f"Analyze this agent definition: {json.dumps(self.agent_data)}"
        print(f"Analysis:\n{response}")

    def do_feedback(self, arg):
        """Get feedback on a specific aspect of the agent definition. Usage: feedback <aspect>"""
        if not self.current_model:
            print("No model selected. Please use 'select_model' first.")
            return
        if not self.agent_data:
            print("No agent definition loaded. Please use 'load_agent' first.")
            return
        if not arg:
            print("Please specify an aspect (input, output, rules, or constraints).")
            return

        provider, model = self.current_model.split(":")
        adm = AgentDialogManager([agent_clarity], model_name=model)
        response = agent_clarity >> f"Provide feedback on the {arg} of this agent definition: {json.dumps(self.agent_data)}"
        print(f"Feedback on {arg}:\n{response}")

    def do_refine(self, arg):
        """Start an interactive refinement session for the loaded agent definition."""
        if not self.current_model:
            print("No model selected. Please use 'select_model' first.")
            return
        if not self.agent_data:
            print("No agent definition loaded. Please use 'load_agent' first.")
            return

        provider, model = self.current_model.split(":")
        adm = AgentDialogManager([agent_clarity], model_name=model)
        
        print("Starting interactive refinement session. Type 'done' to finish.")
        while True:
            user_input = input("Your refinement instruction: ")
            if user_input.lower() == 'done':
                break
            response = agent_clarity >> f"Refine this aspect of the agent definition: {user_input}\nCurrent definition: {json.dumps(self.agent_data)}"
            print(f"Refinement suggestion:\n{response}")
            apply = input("Apply this refinement? (yes/no): ")
            if apply.lower() == 'yes':
                # Here you would update self.agent_data based on the refinement
                print("Refinement applied.")
            else:
                print("Refinement not applied.")

    def do_export(self, arg):
        """Export the refined agent definition. Usage: export <output_file_path>"""
        if not self.agent_data:
            print("No agent definition loaded. Please use 'load_agent' first.")
            return
        if not arg:
            print("Please provide an output file path.")
            return

        try:
            with open(arg, 'w') as f:
                json.dump(self.agent_data, f, indent=2)
            print(f"Agent definition exported to {arg}")
        except IOError:
            print(f"Error writing to file: {arg}")

    def do_exit(self, arg):
        """Exit the Agent Clarity Tool."""
        print("Exiting Agent Clarity Tool. Goodbye!")
        return True

    def default(self, line):
        """Handle unknown commands."""
        print(f"Unknown command: {line}")
        print("Type 'help' or '?' to list available commands.")

def main():
    AgentClarityProcessor().cmdloop()

if __name__ == "__main__":
    main()