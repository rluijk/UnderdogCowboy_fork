import cmd
import os
import re
import json

from pathlib import Path
from prompt_toolkit import prompt
from prompt_toolkit.completion import WordCompleter

from underdogcowboy.core.config_manager import LLMConfigManager
from underdogcowboy import AgentDialogManager, agentclarity, Timeline, adm

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
        self.agents_dir = os.path.expanduser("~/.underdogcowboy/agents")
        self.timeline = Timeline()

    def do_manage_system_message(self, arg):
        """Manage the system message. Usage: manage_system_message"""
        action = input("Enter 'set', 'update', 'delete', or 'view' for system message: ").lower()
        if action in ['set', 'update']:
            message = input("Enter the system message: ")
            self.timeline.set_system_message(message)
            print("System message set/updated.")
        elif action == 'delete':
            self.timeline.delete_system_message()
            print("System message deleted.")
        elif action == 'view':
            system_message = self.timeline.get_system_message()
            if system_message:
                print(f"Current system message: {system_message.text}")
            else:
                print("No system message set.")
        else:
            print("Invalid action. Please try again.")

    def get_available_agents(self):
        """Return a list of available agent files in the agents directory."""
        return [f for f in os.listdir(self.agents_dir) if f.endswith('.json')]

    def do_load_agent(self, arg):
        """Load an agent definition from a JSON file. Usage: load_agent"""
        available_agents = self.get_available_agents()
        
        if not available_agents:
            print("No agent files found in the agents directory.")
            return

        print("Available agents:")
        for i, agent in enumerate(available_agents, 1):
            print(f"{i}. {agent}")

        agent_completer = WordCompleter(available_agents, ignore_case=True)
        while True:
            selection = prompt("Select an agent (type part of the name or number): ", completer=agent_completer)
            
            if selection.isdigit():
                index = int(selection) - 1
                if 0 <= index < len(available_agents):
                    selected_agent = available_agents[index]
                    break
            else:
                matches = [agent for agent in available_agents if selection.lower() in agent.lower()]
                if len(matches) == 1:
                    selected_agent = matches[0]
                    break
                elif len(matches) > 1:
                    print("Multiple matches found. Please be more specific.")
                else:
                    print("No matching agent found. Please try again.")

        agent_path = os.path.join(self.agents_dir, selected_agent)

        try:
            with open(agent_path, 'r') as f:
                self.agent_data = json.load(f)
            self.current_agent_file = agent_path
            print(f"Agent definition loaded from {agent_path}")

            # Update the timeline with the loaded agent data
            self.timeline.load(self.agent_data)
            
            # Update the system message if present in the agent data
            if 'system_message' in self.agent_data:
                system_message = self.agent_data['system_message'].get('text', '')
                self.timeline.set_system_message(system_message)
                print("System message updated from loaded agent.")

        except FileNotFoundError:
            print(f"Agent file not found: {agent_path}")
        except json.JSONDecodeError:
            print(f"Invalid JSON in agent file: {agent_path}")
        except Exception as e:
            print(f"An error occurred while loading the agent: {str(e)}")



    def do_create_agent(self):
        """
        Create a new agent definition and save it to a file.
        """
        agent_name = input("Enter a name for the new agent: ")
        agent_description = input("Enter a description for the new agent: ")
        agent_system_message = input("Enter the system message for the new agent: ")

        # Validation
        if not agent_name:
            print("Error: Agent name cannot be empty.")
            return

        # Python module name validation
        if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", agent_name):
            print("Error: Invalid agent name. Please use only letters, numbers, and underscores. The name must start with a letter or underscore.")
            return

        agents_dir = os.path.expanduser("~/.underdogcowboy/agents")
        os.makedirs(agents_dir, exist_ok=True)
        file_path = os.path.join(agents_dir, f"{agent_name}.json")

        agent_data = {
            "history": [],
            "metadata": {
                "frozenSegments": [],
                "startMode": "interactive",
                "name": agent_name,
                "description": agent_description
            },
            "system_message": {
                "role": "system",
                "text": agent_system_message
            }
        }

        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(agent_data, f, ensure_ascii=False, indent=4)

        print(f"New agent '{agent_name}' created and saved to {file_path}.")

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

    def do_analyze(self, arg):
        """Perform an initial analysis of the loaded agent definition."""
        if not self.current_model:
            print("No model selected. Please use 'select_model' first.")
            return
        if not self.agent_data:
            print("No agent definition loaded. Please use 'load_agent' first.")
            return

        provider, model = self.current_model.split(":")
        adm = AgentDialogManager([agentclarity], model_name=model)
        response = agentclarity >> f"Analyze this agent definition: {json.dumps(self.agent_data)}"
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
        adm = AgentDialogManager([agentclarity], model_name=model)
        response = agentclarity >> f"Provide feedback on the {arg} of this agent definition: {json.dumps(self.agent_data)}"
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
        adm = AgentDialogManager([agentclarity], model_name=model)
        
        print("Starting interactive refinement session. Type 'done' to finish.")
        while True:
            user_input = input("Your refinement instruction: ")
            if user_input.lower() == 'done':
                break
            response = agentclarity >> f"Refine this aspect of the agent definition: {user_input}\nCurrent definition: {json.dumps(self.agent_data)}"
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