import cmd
import json
import os
from prompt_toolkit import prompt, PromptSession
from prompt_toolkit.completion import WordCompleter, Completer, Completion
from prompt_toolkit.document import Document
from prompt_toolkit.shortcuts import CompleteStyle
from ..tools.pdf_generator import PDFGenerator
from ..config_manager import LLMConfigManager

class CommandCompleter(Completer):
    def __init__(self, dialogue_processor):
        self.dialogue_processor = dialogue_processor
        self.commands = [cmd[3:] for cmd in dir(dialogue_processor) if cmd.startswith('do_')]

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
            if command == 'export_pdf':
                save_path = self.dialogue_processor.config_manager.get_general_config()['dialog_save_path']
                for filename in os.listdir(save_path):
                    if filename.endswith('.pdf') and filename.startswith(word_before_cursor):
                        yield Completion(filename, start_position=-len(word_before_cursor))

class DialogueProcessor(cmd.Cmd):   
    intro = "Welcome to the Dialogue Processor. Type 'help' or '?' to list commands."
    prompt = "(dialogue) "

    def __init__(self, config_manager: LLMConfigManager):
        super().__init__()
        self.config_manager = config_manager
        self.pdf_generator = PDFGenerator()
        self.agents_dir = os.path.expanduser('~/.underdogcowboy/agents')
        self.agent_data = None
        self.current_agent_file = None

        # Create a CommandCompleter with all available commands
        self.command_completer = CommandCompleter(self)
        
        # Create a PromptSession with the command completer
        self.session = PromptSession(completer=self.command_completer, complete_style=CompleteStyle.MULTI_COLUMN)

    def get_available_agents(self):
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
        selected_agent = self.prompt_for_agent(agent_completer, available_agents)

        if selected_agent:
            self.load_agent_file(selected_agent)

    def prompt_for_agent(self, agent_completer, available_agents):
        while True:
            selection = prompt("Select an agent (type part of the name or number): ", completer=agent_completer)
            
            if selection.isdigit():
                index = int(selection) - 1
                if 0 <= index < len(available_agents):
                    return available_agents[index]
            else:
                matches = [agent for agent in available_agents if selection.lower() in agent.lower()]
                if len(matches) == 1:
                    return matches[0]
                elif len(matches) > 1:
                    print("Multiple matches found. Please be more specific.")
                else:
                    print("No matching agent found. Please try again.")

    def load_agent_file(self, agent_filename):
        agent_path = os.path.join(self.agents_dir, agent_filename)

        try:
            with open(agent_path, 'r') as f:
                self.agent_data = json.load(f)
            self.current_agent_file = agent_path
            print(f"Agent definition loaded from {agent_path}")
        except FileNotFoundError:
            print(f"Agent file not found: {agent_path}")
        except json.JSONDecodeError:
            print(f"Invalid JSON in agent file: {agent_path}")
        except Exception as e:
            print(f"An error occurred while loading the agent: {str(e)}")

    def do_list(self, arg):
        """List the currently loaded dialogue."""
        if not self.agent_data:
            print("No dialogue loaded. Use 'load_agent' to load a dialogue.")
            return
        
        print(f"Current dialogue: {self.current_agent_file}")
        print(f"Number of exchanges: {len(self.agent_data['history'])}")

    def do_export_pdf(self, arg):
        """Export the current dialogue to a PDF file. Usage: export_pdf <output_filename.pdf>"""
        if not self.agent_data:
            print("No dialogue loaded. Use 'load_agent' to load a dialogue first.")
            return

        if not arg:
            print("Please provide an output filename. Usage: export_pdf <output_filename.pdf>")
            return

        output_file = arg if arg.endswith('.pdf') else arg + '.pdf'
        output_path = os.path.join(self.config_manager.get_general_config()['dialog_save_path'], output_file)

        try:
            # Get the filename from the current_agent_file path
            filename = os.path.basename(self.current_agent_file) if self.current_agent_file else "Unknown"
            
            self.pdf_generator.generate_pdf(output_path, "Dialogue Export", self.agent_data['history'], filename)
            print(f"PDF exported successfully to {output_path}")
        except Exception as e:
            print(f"An error occurred while generating the PDF: {str(e)}")

    def do_show_dialogue(self, arg):
        """Display the current dialogue in the console."""
        if not self.agent_data:
            print("No dialogue loaded. Use 'load_agent' to load a dialogue first.")
            return

        for entry in self.agent_data['history']:
            role = entry['role'].capitalize()
            text = entry['text']
            print(f"{role}: {text}\n")

    def do_help(self, arg):
        """List available commands with their descriptions."""
        print("Available commands:")
        for method in dir(self):
            if method.startswith('do_'):
                command = method[3:]
                doc = getattr(self, method).__doc__
                print(f"  {command}: {doc}")

    def do_exit(self, arg):
        """Exit the Dialogue Processor."""
        print("Exiting Dialogue Processor. Goodbye!")
        return True

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
    config_manager = LLMConfigManager()
    DialogueProcessor(config_manager).cmdloop()

if __name__ == "__main__":
    main()