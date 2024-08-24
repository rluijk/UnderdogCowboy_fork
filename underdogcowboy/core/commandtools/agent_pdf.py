import cmd
import json
import os
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_JUSTIFY
from datetime import date
from prompt_toolkit import prompt
from prompt_toolkit.completion import WordCompleter
from ..config_manager import LLMConfigManager


class DialogueProcessor(cmd.Cmd):
    intro = "Welcome to the Dialogue Processor. Type 'help' or '?' to list commands."
    prompt = "(dialogue) "

    def __init__(self, config_manager: LLMConfigManager):
        super().__init__()
        self.config_manager = config_manager
        self.agents_dir = config_manager.get_agents_directory()
        self.agent_data = None
        self.current_agent_file = None

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

    def do_select(self, arg):
        """Select a specific dialogue if multiple are loaded."""
        print("This feature is not implemented in the current version.")
        print("Use 'load_agent' to load a different dialogue.")

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

        # Create the PDF document
        doc = SimpleDocTemplate(output_path, pagesize=letter,
                                rightMargin=72, leftMargin=72,
                                topMargin=72, bottomMargin=18)

        # Styles
        styles = getSampleStyleSheet()
        styles.add(ParagraphStyle(name='Justify', alignment=TA_JUSTIFY))

        # Custom styles for different roles
        role_styles = {
            'user': ParagraphStyle(
                'User',
                parent=styles['Normal'],
                fontName='Helvetica',
                textColor=colors.darkslategray,
                fontSize=11,
            ),
            'model': ParagraphStyle(
                'Model',
                parent=styles['Normal'],
                fontName='Helvetica-Bold',
                textColor=colors.darkblue,
                fontSize=11,
            )
        }

        # Content
        content = []

        # Title
        content.append(Paragraph("Dialogue Export", styles['Title']))
        content.append(Paragraph(f"Date: {date.today().strftime('%B %d, %Y')}", styles['Normal']))
        content.append(Spacer(1, 12))

        # Dialogue
        for entry in self.agent_data['history']:
            role = entry['role']
            text = entry['text']
            style = role_styles.get(role, styles['Normal'])
            content.append(Paragraph(f"{role.capitalize()}: {text}", style))
            content.append(Spacer(1, 6))

        # Build the PDF
        doc.build(content)

        print(f"PDF exported successfully to {output_path}")

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

def main():
    config_manager = LLMConfigManager()
    DialogueProcessor(config_manager).cmdloop()

if __name__ == "__main__":
    main()