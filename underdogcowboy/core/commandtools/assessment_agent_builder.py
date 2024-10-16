import cmd
import json
import os
from pathlib import Path
from typing import Dict, List

from prompt_toolkit import prompt, PromptSession
from prompt_toolkit.completion import WordCompleter, Completer, Completion
from prompt_toolkit.document import Document
from prompt_toolkit.shortcuts import CompleteStyle

from underdogcowboy.core.config_manager import LLMConfigManager
from underdogcowboy import AgentDialogManager, assessmentbuilder
from underdogcowboy import JSONExtractor

class CommandCompleter(Completer):
    def __init__(self, assessment_builder):
        self.assessment_builder = assessment_builder
        self.commands = [cmd[3:] for cmd in dir(assessment_builder) if cmd.startswith('do_')]

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
            if command == 'init':
                for agent in self.assessment_builder.get_available_agents():
                    if agent.startswith(word_before_cursor):
                        yield Completion(agent, start_position=-len(word_before_cursor))

class AssessmentAgentBuilder(cmd.Cmd):
    intro = "Welcome to the Assessment Agent Builder. Type 'help' or '?' to list commands."
    prompt = "(assess) "
    
    def __init__(self):
        super().__init__()
        self.config_manager = LLMConfigManager()
        self.current_model = None
        self.available_models = self.config_manager.get_available_models()
        
        self.agents_dir = Path.home() / ".underdogcowboy" / "agents"
        self.assessments_dir = Path.home() / ".underdogcowboy" / "assessments"
        self.assessments_dir.mkdir(parents=True, exist_ok=True)
        self.assessment_structure: Dict = {
            "base_agent": "",
            "categories": [],
            "meta_notes": ""
        }
        self.current_category: int = -1
        self.current_assessment_path: Path = None

        # Create a CommandCompleter with all available commands
        self.command_completer = CommandCompleter(self)
        self.num_categories = 5
        
        # Create a PromptSession with the command completer
        self.session = PromptSession(completer=self.command_completer, complete_style=CompleteStyle.MULTI_COLUMN)

    def get_available_agents(self):
        """Return a list of available agent files in the agents directory."""
        return [f for f in os.listdir(self.agents_dir) if f.endswith('.json')]

    def do_init(self, arg):
        """
        Initialize a new assessment agent or load an existing one.

        This command does the following:
        1. If an agent name is provided, it attempts to load that agent's definition.
        2. If the agent exists, it creates a new assessment structure for that agent.
        3. If an assessment already exists for that agent, it loads the existing assessment.
        4. If no agent name is provided, it prompts the user to select from available agents.

        The assessment structure includes:
        - The base agent being assessed
        - Categories for assessment (initially empty)
        - Meta notes for additional context

        Usage: init [agent_name]
        """
        if not arg:
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
                        arg = available_agents[index]
                        break
                else:
                    matches = [a for a in available_agents if selection.lower() in a.lower()]
                    if len(matches) == 1:
                        arg = matches[0]
                        break
                    elif len(matches) > 1:
                        print("Multiple matches found. Please be more specific.")
                    else:
                        print("No matching agent found. Please try again.")

        base_agent_path = self.agents_dir / arg
        if not base_agent_path.exists():
            print(f"Agent file not found: {base_agent_path}")
            return

        self.assessment_structure["base_agent"] = str(base_agent_path)
        self.current_assessment_path = self.assessments_dir / f"assess_{arg}"
        
        if self.current_assessment_path.exists():
            with open(self.current_assessment_path, 'r') as f:
                self.assessment_structure = json.load(f)
            self.num_categories = self.assessment_structure.get("num_categories", 5)
            print(f"Loaded existing assessment from {self.current_assessment_path}")
        else:
            self.assessment_structure["categories"] = []
            self.assessment_structure["meta_notes"] = ""
            self.assessment_structure["num_categories"] = self.num_categories
            print(f"Initialized new assessment for agent {arg}")            

    def do_load(self, arg):
        """
        Load a saved assessment structure.

        This command does the following:
        1. If an assessment name is provided, it attempts to load that assessment.
        2. If no name is provided, it lists all available assessments and prompts the user to select one.
        3. Once an assessment is selected, it loads the assessment structure from the corresponding JSON file.

        The loaded assessment structure includes:
        - The base agent being assessed
        - Defined categories for assessment
        - Any meta notes or additional context

        This allows you to resume work on a previously started assessment or review completed assessments.

        Usage: load [assessment_name]
        """
        available_assessments = self.get_available_assessments()
        
        if not available_assessments:
            print("No assessment files found.")
            return

        if not arg:
            print("Available assessments:")
            for i, assessment in enumerate(available_assessments, 1):
                print(f"{i}. {assessment}")

            assessment_completer = WordCompleter(available_assessments, ignore_case=True)
            while True:
                selection = prompt("Select an assessment (type part of the name or number): ", completer=assessment_completer)
                
                if selection.isdigit():
                    index = int(selection) - 1
                    if 0 <= index < len(available_assessments):
                        selected_assessment = available_assessments[index]
                        break
                else:
                    matches = [a for a in available_assessments if selection.lower() in a.lower()]
                    if len(matches) == 1:
                        selected_assessment = matches[0]
                        break
                    elif len(matches) > 1:
                        print("Multiple matches found. Please be more specific.")
                    else:
                        print("No matching assessment found. Please try again.")
        else:
            if not arg.endswith('.json'):
                arg += '.json'
            if arg not in available_assessments:
                print(f"Assessment file not found: {arg}")
                return
            selected_assessment = arg

        assessment_path = self.assessments_dir / selected_assessment

        try:
            with open(assessment_path, 'r') as f:
                self.assessment_structure = json.load(f)
            self.current_assessment_path = assessment_path
            self.num_categories = self.assessment_structure.get("num_categories", 5)
            print(f"Loaded assessment from {assessment_path}")
        except json.JSONDecodeError:
            print(f"Error: The file {assessment_path} is not a valid JSON file.")
        except Exception as e:
            print(f"An error occurred while loading the assessment: {str(e)}")

    def do_analyze(self, arg):
        """Perform an initial analysis of the loaded agent definition and suggest categories."""
        if not self.validate_current_model():
            return
        if not self.assessment_structure or not self.assessment_structure.get("base_agent"):
            print("No agent definition loaded. Please use 'init' or 'load' command first.")
            return

        try:
            model_name = self.current_model.split(':')[1]
            adm = AgentDialogManager([assessmentbuilder], model_name=model_name)
        except ValueError as e:
            print(f"Error initializing AgentDialogManager: {str(e)}")
            return

        try:
            # Load the agent definition
            with open(self.assessment_structure["base_agent"], 'r') as f:
                agent_data = json.load(f)

            # Prepare existing fixed categories
            fixed_categories = [cat for cat in self.assessment_structure["categories"] if cat.get("fixed", False)]
            num_new_categories = self.num_categories - len(fixed_categories)

            # Instruct the LLM to return categories in a specific JSON format
            prompt = f"""
            Analyze this agent definition and suggest {num_new_categories} new assessment categories for the output it can generate.
            The following categories are already fixed and should not be changed:
            {json.dumps([cat['name'] for cat in fixed_categories])}

            Return your response in the following JSON format:
            {{
                "categories": [
                    {{"name": "Category1", "description": "Description of Category1"}},
                    ... (repeat for the number of new categories)
                ]
            }}
            Agent definition: {json.dumps(agent_data)}
            """
            
            response = assessmentbuilder >> prompt
            print("Analysis complete. Extracting categories...")

            # Define the expected keys for our JSON structure
            expected_keys = ["categories"]

            # Create an instance of JSONExtractor
            extractor = JSONExtractor(response.text, expected_keys)

            # Extract and parse the JSON
            json_data, inspection_data = extractor.extract_and_parse_json()

            # Define expected inspection data
            expected_inspection_data = {
                'number_of_keys': 1,
                'keys': ["categories"],
                'values_presence': {"categories": True},
                'keys_match': True
            }

            # Check the inspection data against the expected data
            is_correct, deviations = extractor.check_inspection_data(expected_inspection_data)

            if is_correct:
                print("Categories extracted successfully.")
                new_categories = json_data["categories"]
                for cat in new_categories:
                    cat["fixed"] = False
                self.assessment_structure["categories"] = fixed_categories + new_categories
                self.do_list_categories(None)
            else:
                print("Error in extracting categories. Deviations found:")
                print(deviations)
                print("Raw response:")
                print(response.text)

        except FileNotFoundError:
            print(f"Agent definition file not found: {self.assessment_structure['base_agent']}")
        except json.JSONDecodeError:
            print(f"Invalid JSON in agent definition file: {self.assessment_structure['base_agent']}")
        except Exception as e:
            print(f"Error during analysis: {str(e)}")
            print("Raw response:")
            print(response.text)    

    def do_toggle_fixed(self, arg):
        """Toggle the fixed status of a category. Usage: toggle_fixed [category_number]"""
        if not self.assessment_structure.get("categories"):
            print("No categories defined. Use 'analyze' to generate categories first.")
            return

        if not arg:
            print("Current categories:")
            for i, category in enumerate(self.assessment_structure["categories"], 1):
                fixed_status = "[FIXED]" if category.get("fixed", False) else ""
                print(f"{i}. {category['name']} {fixed_status}")
            
            while True:
                selection = input("Enter the number of the category to toggle (or 'q' to quit): ")
                if selection.lower() == 'q':
                    return
                if selection.isdigit():
                    arg = selection
                    break
                print("Invalid input. Please enter a number or 'q' to quit.")

        try:
            num = int(arg) - 1
            if 0 <= num < len(self.assessment_structure["categories"]):
                category = self.assessment_structure["categories"][num]
                category["fixed"] = not category.get("fixed", False)
                status = "fixed" if category["fixed"] else "not fixed"
                print(f"Category '{category['name']}' is now {status}.")
            else:
                print(f"Invalid category number. Please choose a number between 1 and {len(self.assessment_structure['categories'])}.")
        except ValueError:
            print("Please provide a valid number.")
            
    def do_list_categories(self, arg):
        """List all current categories. Usage: list_categories"""
        if not hasattr(self, 'assessment_structure') or not self.assessment_structure:
            print("No assessment structure initialized. Use 'init' to start a new assessment.")
            return

        if "categories" not in self.assessment_structure or not self.assessment_structure["categories"]:
            print("No categories defined yet. Use 'analyze' to generate categories or 'add_category' to add one manually.")
            return

        print("Current categories:")
        for i, category in enumerate(self.assessment_structure["categories"], 1):
            try:
                fixed_status = "[FIXED]" if category.get("fixed", False) else ""
                print(f"{i}. {category['name']} {fixed_status}")
            except KeyError:
                print(f"{i}. [Invalid category structure]")

        print(f"\nTotal categories: {len(self.assessment_structure['categories'])}")

    def do_select_category(self, arg):
        """Select a category to work on. Usage: select_category [number]"""
        if "categories" not in self.assessment_structure or not self.assessment_structure["categories"]:
            print("No categories defined yet. Use 'analyze' to generate categories or 'add_category' to add one manually.")
            return

        if not arg:
            print("Current categories:")
            for i, category in enumerate(self.assessment_structure["categories"], 1):
                print(f"{i}. {category['name']}")
            arg = input("Enter the number of the category you want to select: ")

        try:
            num = int(arg) - 1
            if 0 <= num < len(self.assessment_structure["categories"]):
                self.current_category = num
                print(f"Selected category: {self.assessment_structure['categories'][num]['name']}")
            else:
                print(f"Invalid category number. Please choose a number between 1 and {len(self.assessment_structure['categories'])}.")
        except ValueError:
            print("Please provide a valid number.")

    def do_define_category(self, arg):
        """Define or refine the currently selected category. Usage: define_category"""
        if self.current_category == -1:
            print("No category selected. Use 'select_category' first.")
            return
        
        category = self.assessment_structure["categories"][self.current_category]
        if category.get("fixed", False):
            print(f"Warning: Category '{category['name']}' is fixed. Changes will not be saved unless you unfix it first.")
            if input("Do you want to proceed anyway? (y/n): ").lower() != 'y':
                return
        
        print(f"Defining category: {category['name']}")
        
        refined_category = self._refine_category(category["name"], category, input("Your input: "))
        if not category.get("fixed", False):
            self.assessment_structure["categories"][self.current_category] = refined_category
            print("Category updated.")
        else:
            print("Category not updated because it is fixed.")

    def do_set_num_categories(self, arg):
        """Set the number of categories to generate. Usage: set_num_categories [number]"""
        if not arg:
            print(f"Current number of categories: {self.num_categories}")
            arg = input("Enter the new number of categories (1-10): ")
        
        try:
            num = int(arg)
            if 1 <= num <= 10:
                self.num_categories = num
                print(f"Number of categories set to {num}")
            else:
                print("Please provide a number between 1 and 10.")
        except ValueError:
            print("Please provide a valid number.")

    def do_show_num_categories(self, arg):
        """Show the current number of categories. Usage: show_num_categories"""
        print(f"Current number of categories: {self.num_categories}")

    def do_save(self, arg):
        """Save the current assessment structure. Usage: save"""
        if not self.current_assessment_path:
            print("No active assessment. Use 'init' command first.")
            return
        
        self.assessment_structure["num_categories"] = self.num_categories
        with open(self.current_assessment_path, 'w') as f:
            json.dump(self.assessment_structure, f, indent=2)
        print(f"Saved to {self.current_assessment_path}")

    def do_load(self, arg):
        """Load a saved assessment structure. Usage: load [assessment_name]"""
        available_assessments = [f.name for f in self.assessments_dir.glob("assess_*.json")]
        
        if not available_assessments:
            print("No assessment files found.")
            return

        if not arg:
            print("Available assessments:")
            for i, assessment in enumerate(available_assessments, 1):
                print(f"{i}. {assessment}")

            assessment_completer = WordCompleter(available_assessments, ignore_case=True)
            while True:
                selection = prompt("Select an assessment (type part of the name or number): ", completer=assessment_completer)
                
                if selection.isdigit():
                    index = int(selection) - 1
                    if 0 <= index < len(available_assessments):
                        selected_assessment = available_assessments[index]
                        break
                else:
                    matches = [a for a in available_assessments if selection.lower() in a.lower()]
                    if len(matches) == 1:
                        selected_assessment = matches[0]
                        break
                    elif len(matches) > 1:
                        print("Multiple matches found. Please be more specific.")
                    else:
                        print("No matching assessment found. Please try again.")
        else:
            if not arg.endswith('.json'):
                arg += '.json'
            if arg not in available_assessments:
                print(f"Assessment file not found: {arg}")
                return
            selected_assessment = arg

        assessment_path = self.assessments_dir / selected_assessment

        try:
            with open(assessment_path, 'r') as f:
                self.assessment_structure = json.load(f)
            self.current_assessment_path = assessment_path
            print(f"Loaded assessment from {assessment_path}")
        except json.JSONDecodeError:
            print(f"Error: The file {assessment_path} is not a valid JSON file.")
        except Exception as e:
            print(f"An error occurred while loading the assessment: {str(e)}")

    def do_list_assessments(self, arg):
        """List all available assessments. Usage: list_assessments"""
        assessments = list(self.assessments_dir.glob("assess_*.json"))
        if not assessments:
            print("No assessments found.")
            return
        for i, assessment in enumerate(assessments, 1):
            print(f"{i}. {assessment.name}")

    def do_generate_prompt(self, arg):
        """Generate the final system prompt. Usage: generate_prompt"""
        prompt = self._generate_system_prompt(self.assessment_structure)
        print("Generated system prompt:")
        print(prompt)

    def do_exit(self, arg):
        """Exit the program."""
        print("Goodbye!")
        return True

    def do_list_models(self, arg):
        """List all available LLM models."""
        print("Available models:")
        for i, model in enumerate(self.available_models, 1):
            active_indicator = " (***)" if model == self.current_model else ""
            print(f"  {i}. {model}{active_indicator}")
        print("\nTo select a model, use 'select_model <number>' or 'select_model <name>'")
        if self.current_model:
            print(f"Current active model: {self.current_model}")
        else:
            print("No model currently selected.")

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

        if arg.isdigit():
            index = int(arg) - 1
            if 0 <= index < len(self.available_models):
                selected_model = self.available_models[index]
            else:
                print(f"Invalid model number. Please choose between 1 and {len(self.available_models)}.")
                return
        else:
            matching_models = [model for model in self.available_models if arg.lower() in model.lower()]
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

        self.current_model = selected_model
        print(f"Selected model: {selected_model}")

    def _refine_category(self, name: str, current: Dict, user_input: str) -> Dict:
        if not self.validate_current_model():
            return current
        
        try:
            model_name = self.current_model.split(':')[1]
            adm = AgentDialogManager([assessmentbuilder], model_name=model_name)
            
            prompt = f"Refine this assessment category based on user input:\nCategory: {name}\nCurrent definition: {json.dumps(current)}\nUser input: {user_input}"
            response = assessmentbuilder >> prompt
            
            # Parse the response to update the category
            # This is a placeholder and should be adjusted based on the actual response format
            refined = json.loads(response.text)
            return refined
        except Exception as e:
            print(f"Error during category refinement: {str(e)}")
            return current

    def _generate_system_prompt(self, structure: Dict) -> str:
        if not self.validate_current_model():
            return ""
        
        try:
            model_name = self.current_model.split(':')[1]
            adm = AgentDialogManager([assessmentbuilder], model_name=model_name)
            
            prompt = f"Generate a system prompt for an assessment agent based on this structure: {json.dumps(structure)}"
            response = assessmentbuilder >> prompt
            return response.text
        except Exception as e:
            print(f"Error generating system prompt: {str(e)}")
            return ""

    def default(self, line):
        """Handle unknown commands and shortcuts for select_model, select_category, and set_num_categories."""
        if line.isdigit():
            num = int(line)
            if 1 <= num <= len(self.available_models):
                self.do_select_model(line)
            elif 1 <= num <= len(self.assessment_structure.get("categories", [])):
                self.do_select_category(line)
            elif 1 <= num <= 10:
                self.do_set_num_categories(line)
            else:
                print(f"Invalid number. Use 'list_models', 'list_categories', or 'set_num_categories' to see valid options.")
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
    AssessmentAgentBuilder().cmdloop()

if __name__ == "__main__":
    main()