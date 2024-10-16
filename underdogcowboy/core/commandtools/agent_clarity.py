import cmd
import os
import re
import json

from pathlib import Path
from prompt_toolkit import prompt, PromptSession
from prompt_toolkit.completion import WordCompleter, Completer, Completion
from prompt_toolkit.document import Document
from prompt_toolkit.shortcuts import CompleteStyle

from underdogcowboy.core.config_manager import LLMConfigManager
from underdogcowboy import AgentDialogManager, agentclarity, Timeline, adm, AnthropicModel


class CommandCompleter(Completer):
    def __init__(self, agent_clarity_processor):
        self.agent_clarity_processor = agent_clarity_processor
        self.commands = [cmd[3:] for cmd in dir(agent_clarity_processor) if cmd.startswith('do_')]

    def get_completions(self, document, complete_event):
        word_before_cursor = document.get_word_before_cursor(WORD=True)
        line = document.text

        if ' ' not in line:
            # Complete commands
            for command in self.commands:
                if command.startswith(word_before_cursor):
                    yield Completion(command, start_position=-len(word_before_cursor))
        else:
            # Command-specific completions
            command = line.split()[0]
            if command == 'select_model':
                for model in self.agent_clarity_processor.available_models:
                    if model.startswith(word_before_cursor):
                        yield Completion(model, start_position=-len(word_before_cursor))

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

        self.last_analysis = None
        # Create a CommandCompleter with all available commands
        self.command_completer = CommandCompleter(self)

        self.message_export_path = ''
        self.dialog_save_path = ''         
        self.load_config()
        
        # Create a PromptSession with the command completer
        self.session = PromptSession(completer=self.command_completer, complete_style=CompleteStyle.MULTI_COLUMN)

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

    def do_sy(self, arg):
        """Shortcut for system_message command."""
        return self.do_system_message(arg)

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

    def do_create_agent(self,arg):
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

        print(f"New agent '{agent_name}' created and saved to {file_path}.")

    def do_list_models(self, arg):
        """List all available LLM models."""
        print("Available models:")
        for i, model in enumerate(self.available_models, 1):
            print(f"  {i}. {model}")
        print("\nTo select a model, use 'select_model <number>' or 'select_model <name>'")

    def validate_current_model(self):
        if not self.current_model or ':' not in self.current_model:
            print("Invalid model selected. Please use 'select_model' to choose a valid model.")
            return False
        return True

    def do_select_model(self, arg):
        """Select a model to use. Usage: select_model <number or name>"""
        if not arg:
            print("Please provide a model number or name. Use 'list_models' to see available options.")
            return

        available_models = self.config_manager.get_available_models()

        if arg.isdigit():
            index = int(arg) - 1
            if 0 <= index < len(available_models):
                selected_model = available_models[index]
            else:
                print(f"Invalid model number. Please choose between 1 and {len(available_models)}.")
                return
        else:
            matching_models = [model for model in available_models if arg.lower() in model.lower()]
            if len(matching_models) == 1:
                selected_model = matching_models[0]
            elif len(matching_models) > 1:
                print(f"Multiple models match '{arg}'. Please be more specific:")
                for model in matching_models:
                    print(f"  - {model}")
                return
            else:
                print(f"Model '{arg}' not found. Use 'list_models' to see available options.")
                return

        provider, model_id = selected_model.split(':')
        self.config_manager.update_model_property(provider, 'selected_model', model_id)
        self.current_model = selected_model
        print(f"Selected model: {selected_model}")

    def do_analyze(self, arg):
        """Perform an initial analysis of the loaded agent definition."""
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

    def do_feedback_input(self, arg):
        """Get feedback on the input handling of the agent definition."""
        self._get_feedback("input handling")

    def do_feedback_output(self, arg):
        """Get feedback on the output generation of the agent definition."""
        self._get_feedback("output generation")

    def do_feedback_rules(self, arg):
        """Get feedback on the rules of the agent definition."""
        self._get_feedback("rules")

    def do_feedback_constraints(self, arg):
        """Get feedback on the constraints of the agent definition."""
        self._get_feedback("constraints")

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


    def do_exit(self, arg):
        """Exit the Agent Clarity Tool."""
        print("Exiting Agent Clarity Tool. Goodbye!")
        return True

    def default(self, line):
        """Handle unknown commands and shortcut for select_model."""
        if line.isdigit():
            self.do_select_model(line)
        else:
            print(f"Unknown command: {line}")
            print("Type 'help' or '?' to list available commands.")

    def cmdloop(self, intro=None):
        """Repeatedly issue a prompt, accept input, parse an initial prefix
        off the received input, and dispatch to action methods, passing them
        the remainder of the line as argument.
        """
        self.preloop()
        if intro is not None:
            self.intro = intro
        if self.intro:
            self.stdout.write(str(self.intro)+"\n")
        stop = None
        while not stop:
            try:
                line = self.session.prompt(self.prompt)
                line = self.precmd(line)
                stop = self.onecmd(line)
                stop = self.postcmd(stop, line)
            except KeyboardInterrupt:
                print("^C")
            except EOFError:
                print("^D")
                break
        self.postloop()

def main():
    AgentClarityProcessor().cmdloop()

if __name__ == "__main__":
    main()