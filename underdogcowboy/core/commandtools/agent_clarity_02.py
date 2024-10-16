

import os
import json
import sys
import re
from typing import Dict, List, Any 

from prompt_toolkit.completion import WordCompleter
from prompt_toolkit import prompt

from pathlib import Path
from uccli import StorageManager, GenericCLI, StateMachine, State, command, cancellable_command,input_required_command, CommandCompleter


from underdogcowboy.core.config_manager import LLMConfigManager 
from underdogcowboy import UCAgentCommunicator, AgentDialogManager, Timeline, adm, AnthropicModel

# Import agentclarity and cliagent from their specific modules
from underdogcowboy  import cliagent

class AgentClarityProcessor(GenericCLI):
    def __init__(self):

        self.config_manager = LLMConfigManager()

        self.uc_agent_communicator = UCAgentCommunicator(cliagent)
        
        self.current_model = None
        self.available_models = self.config_manager.get_available_models()
        
        self.current_agent_file = None
        self.agent_data = None
        self.agents_dir = os.path.expanduser("~/.underdogcowboy/agents")
        self.timeline = Timeline()

        self.last_analysis = None
     
        self.message_export_path = ''
        self.dialog_save_path = ''         
        self.load_config()
        

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

        #super().__init__(state_machine)
        super().__init__(state_machine, agent_communicator=self.uc_agent_communicator)
       
          # Initialize the storage system
        self.storage_manager = StorageManager(base_dir=os.path.expanduser("~/.uccli_sessions"))
        self.current_storage = None

        # Load or create a default session --> SharedStorage
        default_session_name = "default_session"
        try:
            self.current_storage = self.storage_manager.load_session(default_session_name)
            print(f"Loaded default session: {default_session_name}")
        except ValueError:
            self.current_storage = self.storage_manager.create_session(default_session_name)
            print(f"Created new default session: {default_session_name}")


            
    @command("print_state_machine", "Print the current state machine configuration")
    def do_print_state_machine(self, arg):
        print("State Machine Configuration:")
        for state in self.state_machine.states:
            print(f"\nState: {state.name}")
            for command, next_state in state.transitions.items():
                print(f"  {command} -> {next_state.name}")

    @command("load_agent", "Load an agent definition from a JSON file")
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
                print("System message found in agent data.")
                system_message_dict = self.agent_data['system_message']
                print(f"System message dict: {system_message_dict}")
                
                if isinstance(system_message_dict, dict):
                    system_message = system_message_dict.get('content') or system_message_dict.get('text', '')
                    print(f"Extracted system message: {system_message}")
                else:
                    print(f"Unexpected system_message type: {type(system_message_dict)}")
                    system_message = str(system_message_dict)

                self.timeline.set_system_message(system_message)
                print(f"System message loaded: {system_message}")
            else:
                print("No system message found in the agent definition.")

            print("Use 'system_message set|view|delete' to manage the system message.")

        except FileNotFoundError:
            print(f"Agent file not found: {agent_path}")
        except json.JSONDecodeError:
            print(f"Invalid JSON in agent file: {agent_path}")
        except Exception as e:
            print(f"An error occurred while loading the agent: {str(e)}")
            print(f"Error type: {type(e)}")
            print(f"Error args: {e.args}")
            import traceback
            traceback.print_exc()
        print("load_agent command executed")

    @command("create_agent", "Create a new agent definition")
    def do_create_agent(self, arg):
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
                "content": agent_system_message
            }
        }

        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(agent_data, f, ensure_ascii=False, indent=4)

        self.current_storage.update_data('agent_state', agent_data)


        print(f"New agent '{agent_name}' created and saved to {file_path}.")
        print("create_agent command executed")

    @input_required_command(
        prompt="Please enter a model number or name: ",
        error_message="No model selected. Use 'list_models' to see available options."
    )
    @command("select_model", "Select a model to use")
    def do_select_model(self, arg):
        """Select a model to use. Usage: select_model <number or name>"""
        available_models = self.config_manager.get_available_models()

        if arg.lower() == 'list_models':
            self.do_list_models('')
            return False

        if arg.isdigit():
            index = int(arg) - 1
            if 0 <= index < len(available_models):
                selected_model = available_models[index]
            else:
                print(f"Invalid model number. Please choose between 1 and {len(available_models)}.")
                return False
        else:
            matching_models = [model for model in available_models if arg.lower() in model.lower()]
            if len(matching_models) == 1:
                selected_model = matching_models[0]
            elif len(matching_models) > 1:
                print(f"Multiple models match '{arg}'. Please be more specific:")
                for model in matching_models:
                    print(f"  - {model}")
                return False
            else:
                print(f"Model '{arg}' not found. Use 'list_models' to see available options.")
                return False

        provider, model_id = selected_model.split(':')
        self.config_manager.update_model_property(provider, 'selected_model', model_id)
        self.current_model = selected_model
        print(f"Selected model: {selected_model}")
        print("select_model command executed")
        

    @cancellable_command("Are you sure you want to proceed with the analysis? (y/n): ")
    @command("analyze", "Perform an initial analysis of the loaded agent definition")
    def do_analyze(self, arg):
        """Perform an initial analysis of the loaded agent definition."""
        print("Starting analysis...")
       
        if not self.validate_current_model():
            return
        if not self.agent_data:
            print("No agent definition loaded. Please use 'load_agent' first.")
            return

        try:
            model_name = self.current_model.split(':')[1]
            adm = AgentDialogManager([agentclarity], model_name=model_name)
        except ValueError as e:
            print(f"Error initializing AgentDialogManager: {str(e)}")
            return

        try:
            response = agentclarity >> f"Analyze this agent definition: {json.dumps(self.agent_data)}"
            print(f"Analysis:\n{response}")
            self.last_analysis = response.text
        except Exception as e:
            print(f"Error during analysis: {str(e)}")
            self.last_analysis = None
 
        print("Analysis complete.")
        print("Available commands in this state: export_analysis, feedback, feedback_input, feedback_output, feedback_rules, feedback_constraints")
        

    @command("export_analysis", "Export the last analysis to a markdown file")
    def do_export_analysis(self, arg):
        """Export the last analysis to a markdown file. Usage: export_analysis <filename>"""
        if not self.last_analysis:
            print("No analysis has been performed yet. Please use 'analyze' first.")
            return
        if not arg:
            print("Please provide a filename for the markdown file.")
            return

        filename = arg if arg.endswith('.md') else f"{arg}.md"
        
        # Use the configured message_export_path if available
        if self.message_export_path:
            export_path = os.path.join(self.message_export_path, filename)
        else:
            export_path = filename  # Use the current directory if no export path is configured

        try:
            # Ensure the directory exists
            os.makedirs(os.path.dirname(export_path), exist_ok=True)

            # Create the markdown file
            with open(export_path, 'w') as f:
                f.write(self.last_analysis)
            
            print(f"Analysis exported to '{export_path}'.")
        except Exception as e:
            print(f"Error during file creation: {str(e)}")

        print("export_analysis command executed")

    @command("feedback", "Get general feedback on the agent definition")
    def do_feedback(self, arg):
        """Get feedback on a specific aspect of the agent definition. Usage: feedback <aspect>"""
        if not self.validate_current_model():
            return
        if not self.agent_data:
            print("No agent definition loaded. Please use 'load_agent' first.")
            return
        if not arg:
            print("Please specify an aspect (input, output, rules, or constraints).")
            return

        try:
            adm = AgentDialogManager([agentclarity], model_name=self.current_model)
        except ValueError as e:
            print(f"Error initializing AgentDialogManager: {str(e)}")
            return

        try:
            response = agentclarity >> f"Provide feedback on the {arg} of this agent definition: {json.dumps(self.agent_data)}"
            print(f"Feedback on {arg}:\n{response}")
        except Exception as e:
            print(f"Error during feedback: {str(e)}")        
        print("feedback command executed")

    @command("feedback_input", "Get feedback on the input handling of the agent definition")
    def do_feedback_input(self, arg):
        """Get feedback on the input handling of the agent definition."""
        self._get_feedback("input handling")        
        print("feedback_input command executed")

    @command("feedback_output", "Get feedback on the output generation of the agent definition")
    def do_feedback_output(self, arg):
        """Get feedback on the output generation of the agent definition."""
        self._get_feedback("output generation")
        print("feedback_output command executed")

    @command("feedback_rules", "Get feedback on the rules of the agent definition")
    def do_feedback_rules(self, arg):
        """Get feedback on the rules of the agent definition."""
        self._get_feedback("rules")
        print("feedback_rules command executed")

    @command("feedback_constraints", "Get feedback on the constraints of the agent definition")
    def do_feedback_constraints(self, arg):
        """Get feedback on the constraints of the agent definition."""
        self._get_feedback("constraints")        
        print("feedback_constraints command executed")

    @command("system_message", "Manage the system message for the currently loaded agent")
    def do_system_message(self, arg):
        """Manage the system message for the currently loaded agent. Usage: system_message [set|view|delete]"""
        if not self.agent_data:
            print("No agent loaded. Please use 'load_agent' first.")
            return

        actions = ['set', 'view', 'delete']
        
        if not arg:
            action = input("Enter action (set, view, delete): ").lower().strip()
        else:
            action = arg.lower().strip()

        # Handle partial matches
        matches = [a for a in actions if a.startswith(action)]
        if len(matches) == 1:
            action = matches[0]
        elif len(matches) > 1:
            print(f"Ambiguous action. Did you mean one of these: {', '.join(matches)}?")
            return
        elif not matches:
            print("Invalid action. Use 'set', 'view', or 'delete'.")
            return

        update_file = False

        if action == 'set':
            message = input("Enter the system message: ")
            self.timeline.set_system_message(message)
            self.agent_data['system_message'] = {'role': 'system', 'content': message}
            print("System message set/updated for the current agent.")
            update_file = True
        elif action == 'delete':
            self.timeline.delete_system_message()
            if 'system_message' in self.agent_data:
                del self.agent_data['system_message']
            print("System message deleted for the current agent.")
            update_file = True
        elif action == 'view':
            system_message = self.agent_data.get('system_message', {}).get('content') or self.agent_data.get('system_message', {}).get('text', '')
            if system_message:
                print(f"Current system message: {system_message}")
            else:
                print("No system message set for the current agent.")

        # Save the updated agent data to file only if changes were made
        if update_file and self.current_agent_file:
            with open(self.current_agent_file, 'w') as f:
                json.dump(self.agent_data, f, indent=2)
            print(f"Agent definition updated in {self.current_agent_file}")

        print("system_message command executed")

    @command("list_models", "List all available LLM models")
    def do_list_models(self, arg):
        """List all available LLM models."""
        print("Available models:")
        for i, model in enumerate(self.available_models, 1):
            print(f"  {i}. {model}")
        print("\nTo select a model, use 'select_model <number>' or 'select_model <name>'")

    @command("reset", "Reset the process and return to the initial state")
    def do_reset(self, arg):
        print("Resetting to initial state")
        self.state_machine.current_state = self.state_machine.initial_state


    @command("exit", "Exit the Agent Clarity Tool")
    def do_exit(self, arg):
        print("Exiting Agent Clarity Tool. Goodbye!")
        return "EXIT"

    def load_config(self):
        """
        Load configuration settings from a JSON file.
        
        Reads the configuration file and sets up message export and dialog save paths.
        """        
        config_file = os.path.join(Path.home(), '.underdogcowboy', 'config.json')

        if os.path.exists(config_file):
            with open(config_file, 'r') as f:
                config = json.load(f)
                
            general_config = config.get('general', {})
            self.message_export_path = os.path.abspath(general_config.get('message_export_path', ''))
            self.dialog_save_path = os.path.abspath(general_config.get('dialog_save_path', ''))

            if not self.message_export_path or not self.dialog_save_path:
                print("Warning: Some configuration values are missing.")
        else:
            print(f"Configuration file '{config_file}' not found.")
            self.message_export_path = ''
            self.dialog_save_path = ''   

    def get_available_agents(self):
        """Return a list of available agent files in the agents directory."""
        return [f for f in os.listdir(self.agents_dir) if f.endswith('.json')]
    
    def validate_current_model(self):
        if not self.current_model or ':' not in self.current_model:
            print("Invalid model selected. Please use 'select_model' to choose a valid model.")
            return False
        return True
    
    def _get_feedback(self, aspect):
        if not self.validate_current_model():
            return
        if not self.agent_data:
            print("No agent definition loaded. Please use 'load_agent' first.")
            return

        try:
            model_name = self.current_model.split(':')[1]
            adm = AgentDialogManager([agentclarity], model_name=model_name)
        except ValueError as e:
            print(f"Error initializing AgentDialogManager: {str(e)}")
            return

        try:
            response = agentclarity >> f"Provide detailed feedback on the {aspect} of this agent definition: {json.dumps(self.agent_data)}"
            print(f"Feedback on {aspect}:\n{response}")
            self.last_analysis = response.text
        except Exception as e:
            print(f"Error during feedback: {str(e)}")

def main():
    AgentClarityProcessor().cmdloop()

if __name__ == "__main__":
    main()