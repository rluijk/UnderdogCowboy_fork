import threading
import time
import logging

import os
import json
import sys
import re

# from rich import print
from pathlib import Path

from prompt_toolkit import prompt
from prompt_toolkit.completion import WordCompleter

from .model import ModelManager, ModelRequestException
from .config_manager import LLMConfigManager
from .llm_response_markdown import LLMResponseRenderer

from .exceptions import InvalidAgentNameError

from .json_storage import TimelineStorage

'''
The Timeline and CommandProcessor classes work together to manage a conversational history and process user commands. 
The CommandProcessor acts as a controller, utilizing the Timeline to store and manipulate the conversation data.

The integration between Timeline and CommandProcessor follows a controller-model pattern. 
The CommandProcessor acts as an interface between the user and the Timeline, translating user commands into 
operations on the conversation history stored in the Timeline. This separation of concerns allows for a clear
division of responsibilities: Timeline manages the data structure and persistence, while CommandProcessor handles
user interaction and command execution.
'''




renderer = LLMResponseRenderer(
    mdformat_config_path=None,  # Provide path if you have a custom config
)



class Message:
    def __init__(self, role, text):
        self.role = role
        self.text = text

class Timeline:
    def __init__(self):
        """
        Initialize a new Timeline instance.
        
        Sets up the history, current position, frozen segments, start mode, and loaded filename.
        """
        self.history = []
        self.current_position = 0
        self.frozen_segments = []
        self.start_mode = 'interactive'
        self.loaded_filename = None
        self.system_message = None
        self.storage = TimelineStorage()

        

    def set_system_message(self, message):
        """Set or update the system message."""
        self.system_message = Message('system', message)

    def delete_system_message(self):
        """Delete the system message."""
        self.system_message = None

    def get_system_message(self):
        """Get the current system message."""
        return self.system_message

    def display_timeline(self):
        """
        Display a visual representation of the timeline.
        
        Shows frozen segments and interactive messages, with the current position marked as 'H'.
        """        
        visual_representation = []
        last_frozen_end_index = -1

        # Iterate through frozen segments
        for segment in self.frozen_segments:
            frozen_indices = [str(i) if i != self.current_position else "H" for i in
                              range(segment['start'], segment['end'] + 1)]
            visual_representation.append(f"F({','.join(frozen_indices)})")

            # Check for interactive messages between frozen segments
            if segment['end'] < len(self.history) - 1:
                interactive_start = segment['end'] + 1
                next_frozen_start = self.frozen_segments[0]['start'] if self.frozen_segments else len(self.history)

                for idx in range(interactive_start, min(next_frozen_start, len(self.history))):
                    if idx == self.current_position:
                        visual_representation.append("H")
                    else:
                        visual_representation.append(str(idx))

            last_frozen_end_index = segment['end']

        # Display any remaining interactive messages after the last frozen segment
        if last_frozen_end_index < len(self.history) - 1:
            interactive_indices = [str(i) if i != self.current_position else "H" for i in
                                   range(last_frozen_end_index + 1, len(self.history))]
            visual_representation.extend(interactive_indices)

        print("Timeline Segments:")
        print(' '.join(visual_representation))

    def select_message(self):
        """
        Allow the user to select a message from the history.
        
        Returns:
            int or None: The index of the selected message, or None if selection is invalid.
        """        
        if not self.history:
            print("No messages in history.")
            return None

        summaries = [f"{i}: {' '.join(msg.text.split()[:10])}" for i, msg in enumerate(self.history)]
        completer = WordCompleter(summaries, ignore_case=True)

        selection = prompt('Select a message: ', completer=completer)
        try:
            selected_index = int(selection.split(':')[0])
            return selected_index
        except (ValueError, IndexError):
            print("Invalid selection.")
            return None

    def add_message(self, role, text):
        """
        Add a new message to the timeline.
        
        Args:
            role (str): The role of the message sender (e.g., 'user' or 'model').
            text (str): The content of the message.
        """
        message = Message(role, text)
        # Determine the insertion point: right after the current_position
        insert_index = self.current_position + 1
        # Insert the new message
        self.history.insert(insert_index, message)
        # Update current_position to reflect the position of the newly added message
        self.current_position = insert_index
      
    def export_message_to_markdown(self, index, filename):
        """
        Export a specific message to a Markdown file.
        
        Args:
            index (int): The index of the message to export.
            filename (str): The name of the file to save the exported message.
        """
        if 0 <= index < len(self.history):
            msg = self.history[index]
            markdown_content = f"---\n" \
                               f"title: Message at Index {index}\n" \
                               f"role: {msg.role.capitalize()}\n" \
                               f"source_file: {self.loaded_filename}\n" \
                               f"---\n\n" \
                               f"{msg.text}\n"
            with open(filename, 'w', encoding='utf-8') as md_file:
                md_file.write(markdown_content)
            print(f"Message exported to Markdown file '{filename}' successfully.")
        else:
            print(f"No message found at index {index}.")

    def get_current_position(self):
        """
        Get the current position in the timeline.
        
        Returns:
            int: The index of the current position.
        """
        return self.current_position

    def head(self):
        """
        Display information about the current state of the timeline.
        
        Shows the total number of messages and the current position.
        """        
        print(f"Total messages in history: {len(self.history)}")
        print(f"Current position in timeline: Message {self.current_position}")

    def display_item(self, index):
        """
        Display a specific item from the timeline.
        
        Args:
            index (int): The index of the item to display.
        """        
        if 0 <= index < len(self.history):
            msg = self.history[index]
            role = "User" if msg.role == 'user' else "Model"
            print(f"Item at index {index}: {role}: {msg.text}")
        else:
            print(f"No item found at index {index}")

    def save(self, filename, name=None, description=None, path=None):
        if not name:
            name = input("Enter a name for this timeline session: ")
        if not description:
            description = input("Enter a description for this timeline session: ")

        start_mode = 'frozen' if self.frozen_segments and self.frozen_segments[0]['start'] == 0 else 'interactive'

        data = {
            "history": [msg.__dict__ for msg in self.history],
            "metadata": {
                "frozenSegments": self.frozen_segments,
                "startMode": start_mode,
                "name": name,
                "description": description
            },
            "system_message": self.system_message.__dict__ if self.system_message else None
        }

        self.storage.save_timeline(data, filename, path)

    def __bck__save(self, filename, name=None, description=None, path=None):
        """
        Save the current timeline to a file.
        
        Args:
            filename (str): The name of the file to save.
            name (str, optional): The name of the timeline session.
            description (str, optional): A description of the timeline session.
            path (str, optional): The directory path to save the file.
        """
        if not name:
            name = input("Enter a name for this timeline session: ")
        if not description:
            description = input("Enter a description for this timeline session: ")

        if path:
            full_path = os.path.join(path, filename)
        else:
            full_path = filename

        # Determine the start_mode based on the position of the first frozen segment
        if self.frozen_segments and self.frozen_segments[0]['start'] == 0:
            start_mode = 'frozen'
        else:
            start_mode = 'interactive'

        # Metadata now includes name and description
        metadata = {
            "frozenSegments": self.frozen_segments,
            "startMode": start_mode,
            "name": name,
            "description": description
        }

        # Prepare the data dictionary with additional metadata
        data = {
            "history": [msg.__dict__ for msg in self.history],
            "metadata": metadata,
            "system_message": self.system_message.__dict__ if self.system_message else None

        }

        # Writing to file
        with open(full_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        # print(f"Timeline saved to {filename} with name '{name}' and description: '{description}'")

    def load(self, source, path=None):
        """
        Load a timeline from a dictionary, file, or JSON string.
        
        Args: 
            source (dict or str): The timeline data as a dictionary, or the name of the file to load, or a JSON string.
            path (str, optional): The directory path of the file (if loading from a file).
        """
        if isinstance(source, dict):
            # If source is already a dictionary, use it directly
            data = source
            self.loaded_filename = None
        elif isinstance(source, str):
            if path:
                full_path = os.path.join(path, source)
                with open(full_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self.loaded_filename = source
            else:
                try:
                    # Try to parse source as JSON string
                    data = json.loads(source)
                    self.loaded_filename = None
                except json.JSONDecodeError:
                    # If parsing fails, treat source as a filename
                    with open(source, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    self.loaded_filename = source
        else:
            raise ValueError("Source must be either a dictionary or a string")

        # Clear existing data
        self.history.clear()
        self.frozen_segments.clear()

        try:
            self.system_message = self.reconstruct_message(data.get('system_message')) if data.get('system_message') else None
        except KeyError as e:
            print(f"Warning: Failed to load system message. Key not found: {e}")
            self.system_message = None

        # Retrieve the original history and frozen segment details
        initial_history = data.get('history', [])
        original_frozen_segments = data.get('metadata', {}).get('frozenSegments', [])
        self.start_mode = data.get('metadata', {}).get('startMode', 'interactive')

        if not original_frozen_segments:
            # Load entire history if there are no frozen segments
            for message_data in initial_history:
                self.history.append(self.reconstruct_message(message_data))
            # Set current position to the end of the history if no frozen segments
            self.current_position = len(self.history) - 1
        else:
            # Only load messages within the frozen segments
            new_index = 0
            index_mapping = {}
            for segment in original_frozen_segments:
                for idx in range(segment['start'], segment['end'] + 1):
                    self.history.append(self.reconstruct_message(initial_history[idx]))
                    index_mapping[idx] = new_index
                    new_index += 1

            # Update the start and end indices of each frozen segment based on the new positions
            for segment in original_frozen_segments:
                new_start = index_mapping[segment['start']]
                new_end = index_mapping[segment['end']]
                self.frozen_segments.append({'start': new_start, 'end': new_end})

            # Set current position to the start of the first frozen segment
            self.current_position = self.frozen_segments[0]['start']

        # self.loaded_filename = filename
        # print( f"Timeline loaded from {self.loaded_filename}, starting in {self.start_mode} mode with current position at index {self.current_position}.")

    def reconstruct_message(self, message_data):
        """
        Reconstruct a Message object from loaded data.
        
        Args:
            message_data (dict): The data of the message to reconstruct.
        
        Returns:
            Message: The reconstructed Message object.
        """
        role = message_data['role']
        text = message_data.get('text') or message_data.get('content', '')

        if text.startswith('File sent: '):
            file_path_part = text.split('File sent: ')[1]
            file_path = file_path_part.split('\n\nFile Content:\n')[0]
            base_text = text.split('\n\nFile Content:\n')[0]
            try:
                with open(file_path, 'r') as file:
                    file_content = file.read()
                reconstructed_text = f"{base_text}\n\nFile Content:\n{file_content}"
            except FileNotFoundError:
                reconstructed_text = f"{base_text}\nError: File not found at '{file_path}'"
        else:
            reconstructed_text = text

        return Message(role, reconstructed_text)

class ExitCommandException(Exception):
    """Custom exception to handle exit command."""
    pass

class CommandProcessor:
    def __init__(self, timeline, model):
        """
        Initialize the CommandProcessor.
        
        Args:
            timeline (Timeline): The Timeline instance to process.
            model: The model used for generating responses.
        """
        self.timeline = timeline
        self.model = model
        self.initialize_commands()
        self.load_config()

        print("Interactive mode started.")

    def manage_system_message(self):
        """Manage the system message."""
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

    def exit_command(self):
        """Raise an exception to exit the command loop."""
        raise ExitCommandException("Exiting command processor.")
    
    def process_file_input(self, file_path):
        # Convert to absolute path if it's not already
        abs_file_path = os.path.abspath(file_path)
        
        if os.path.exists(abs_file_path):
            try:
                with open(abs_file_path, 'r') as f:
                    file_content = f.read()
                if file_content.strip():
                    message = f"File sent: {abs_file_path}\n\nFile Content:\n{file_content}"
                    return message
                else:
                    print("File is empty. Not sending.")
                    return False
            except Exception as e:
                print(f"Error reading file: {e}")
                return False
        else:
            print(f"File not found: {abs_file_path}")
            return False     

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

    def initialize_commands(self):
        """
        Initialize the command dictionary.
        
        Maps command strings to their corresponding methods.
        """        
        self.commands = {
            'interactive': self.interactive_phase,
            'i': self.interactive_phase,
            'display-timeline': self.display_timeline,
            'dt': self.display_timeline,
            'save-timeline': self.save_timeline,
            's': self.save_timeline,
            'save-agent': self.save_agent,
            'sa': self.save_agent, 
            'load-timeline': self.load_timeline,
            'l': self.load_timeline,
            'export-markdown': self.export_to_markdown,
            'e': self.export_to_markdown,
            'head': self.head,
            'h': self.head,
            'display-item': self.display_item,
            'd': self.display_item,
            'select-message': self.select_message,
            'sm': self.select_message,
            'system-message': self.manage_system_message,
            'sysm': self.manage_system_message,
            'help': self.help,
            '?': self.help,
            'quit': self.exit_command,
            'q': self.exit_command,
            'select-dialog': self.load_selected_dialog,
            'sd': self.load_selected_dialog,
            'select-agent' : self.load_selected_agent,
            'sla' : self.load_selected_agent,
            'switch-model': self.switch_model,  
            'swm': self.switch_model  
  
        }

    def switch_model(self):
        config_manager = LLMConfigManager()
        available_models = config_manager.get_available_models()
        
        print("Available models:")
        for i, model_name in enumerate(available_models, 1):
            print(f"{i}. {model_name}")
        
        while True:
            try:
                choice = int(input("Enter the number of the model you want to switch to: "))
                if 1 <= choice <= len(available_models):
                    new_model_name = available_models[choice - 1]
                    break
                else:
                    print("Invalid choice. Please try again.")
            except ValueError:
                print("Please enter a valid number.")
                
        provider, model_name = new_model_name.split(":")
        new_model = ModelManager.initialize_model_with_id(provider, model_name)
        self.model = new_model
        print(f"Switched to {model_name} model.")

        return 

    def display_timeline(self):
        """
        Display the timeline.
        
        Calls the display_timeline method of the Timeline instance.
        """        
        self.timeline.display_timeline()

    def process_command(self, command):
        """
        Process a given command by executing the corresponding method.

        This method checks if the command exists in the self.commands dictionary.
        If it does, it executes the associated method and handles any potential
        exceptions. If the command execution returns an integer, it updates the
        timeline's current position. If the command is not recognized, it prints
        an error message.

        Args:
            command (str): The command to process.

        Returns:
            int: The current position in the timeline after processing the command.

        Raises:
            No exceptions are raised by this method itself, but it catches and
            prints any exceptions raised by the executed command methods.

        Side Effects:
            - May update self.timeline.current_position if the command returns an integer.
            - Prints error messages for invalid commands or execution errors.
        """
        if command in self.commands:
            try:
                result = self.commands[command]()
                if result is not None and isinstance(result, int):
                    self.timeline.current_position = result
            except Exception as e:
                print(f"Error executing command '{command}': {e}")
        else:
            print("Invalid command. Type 'help' to see the list of available commands.")
        return self.timeline.get_current_position()

    def list_all_dialogs(self, root_path):
        """
        List all dialog files in the given root path.

        Args:
            root_path (str): The root directory to search for dialog files.

        Returns:
            list: A list of dialog names with their relative paths.
        """        
        dialog_names = []

        for dirpath, _, filenames in os.walk(root_path):
            for file in filenames:
                if file.endswith('.json'):
                    full_path = os.path.join(dirpath, file)
                    relative_path = os.path.relpath(full_path, root_path)  # Include the relative path from root
                    try:
                        with open(full_path, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                        dialog_name = data['metadata'].get('name', 'Unnamed Dialog')
                        dialog_names.append(f"{dialog_name} ({relative_path})")
                    except Exception as e:
                        print(f"Failed to read {file}: {e}")
                        continue

        return dialog_names

    def list_dialogs_for_selection(self):
        """
        List all dialogs available for selection.

        Returns:
            list: A list of dialog names with their relative paths.
        """        
        root_path = self.dialog_save_path  # Set the root directory for dialog histories
        dialog_names = []

        for dirpath, _, filenames in os.walk(root_path):
            for file in filenames:
                if file.endswith('.json'):
                    full_path = os.path.join(dirpath, file)
                    try:
                        with open(full_path, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                        dialog_name = data['metadata'].get('name', 'Unnamed Dialog')
                        relative_path = os.path.relpath(full_path, root_path)  # Get relative path from root
                        dialog_names.append(f"{dialog_name} ({relative_path})")
                    except Exception as e:
                        print(f"Failed to read {file}: {e}")
                        continue

        return dialog_names

    def select_agent(self):
        agents_dir = os.path.expanduser("~/.underdogcowboy/agents")

         # Create the directory if it doesn't exist
        os.makedirs(agents_dir, exist_ok=True)

        agent_names = self.list_all_dialogs(agents_dir)

        if not agent_names:
            print("No user defined agents available to select")
            return None

        dialog_completer = WordCompleter(agent_names, ignore_case=True, match_middle=True)
        selection = prompt("Select a dialog (type to filter): ", completer=dialog_completer)

        try:
            # Extract the relative path from the selection
            relative_path = selection.split('(')[-1].strip(') ')
            full_path = os.path.join(agents_dir, relative_path)
            return full_path
        except IndexError:
            print("Invalid selection.")
            return None    

    def load_selected_agent(self):
        """
        Load a agent selected by the user.

        Prompts the user to select a agents and loads it into the timeline.
        """        
        filepath = self.select_agent()
        if filepath:
            self.timeline.load(filepath)
            print(f"Agent loaded from {filepath}.")
        else:
            print("Agent loading canceled.")

    def select_dialog(self):
        """
        Allow the user to select a dialog from the available options.

        Returns:
            str or None: The full path of the selected dialog, or None if selection is cancelled.
        """        
        dialog_names = self.list_all_dialogs(self.dialog_save_path)
        if not dialog_names:
            print("No dialogs available to select.")
            return None

        dialog_completer = WordCompleter(dialog_names, ignore_case=True, match_middle=True)
        selection = prompt("Select a dialog (type to filter): ", completer=dialog_completer)

        try:
            # Extract the relative path from the selection
            relative_path = selection.split('(')[-1].strip(') ')
            full_path = os.path.join(self.dialog_save_path, relative_path)
            return full_path
        except IndexError:
            print("Invalid selection.")
            return None

    def load_selected_dialog(self):
        """
        Load a dialog selected by the user.

        Prompts the user to select a dialog and loads it into the timeline.
        """        
        filepath = self.select_dialog()
        if filepath:
            self.timeline.load(filepath)
            print(f"Dialog loaded from {filepath}.")
        else:
            print("Dialog loading canceled.")


    def help(self):
        """
        Display help information about available commands.

        Prints a list of commands and their descriptions.
        """        
        print("Available commands and shortcuts:")
        print("  interactive, i: Enter interactive mode to chat with the model.")
        print("  system-message, sysm: Manage the system message.")
        print("  save-timeline, s: Save the current timeline to a file.")
        print("  load-timeline, l: Load a timeline from a file.")
        print("  export-markdown, e: Export a message to Markdown.")
        print("  head, h: Display the current position in the timeline.")
        print("  display-item, d: Display a specific item from the timeline by index.")
        print("  display-timeline, dt: Display runtime timeline.")
        print("  save-agent, sa: Save your dialog as an agent.")
        print("  select-message, sm: Select a specific message by index.")
        print("  select-dialog, sd: Select a specific dialog.")
        print("  select-agent, sla: Select a specific agent.")
        print("  switch-model, swm: Switch LLM model.")
        print("  help, ?: Show this help message.")
        print("  quit, q: Exit the application.")
       
    def select_message(self):
        """
        Allow the user to select a specific message from the timeline.

        Displays the selected message after selection.
        """        
        selected_index = self.timeline.select_message()
        if selected_index is not None:
            self.timeline.display_item(selected_index)
    
    def export_to_markdown(self):
        """
        Export a selected message to a Markdown file.

        Prompts the user for the message index and filename, then exports the message.
        """        
        try:
            index = int(input("Enter the index of the message to export: "))
            filename_input = input("Enter the filename for the Markdown file (without extension): ").strip()
            if not filename_input:
                raise ValueError("Filename cannot be empty.")
            filename = filename_input + '.md'

            # Check if message_export_path is defined
            if not self.message_export_path:
                raise ValueError("Export folder is not defined in the configuration. Please update your configuration.")

            # Create the directory if it doesn't exist
            export_path = Path(self.message_export_path)
            export_path.mkdir(parents=True, exist_ok=True)

            full_path = export_path / filename
            
            # Attempt to export the message
            self.timeline.export_message_to_markdown(index, str(full_path))
            print(f"Message exported successfully to {full_path}")

        except ValueError as e:
            print(f"Input error: {e}")
        except Exception as e:
            print(f"An unexpected error occurred: {e}")

    def load_timeline(self):
        """
        Load a timeline from a file.

        Prompts the user for the filename and loads the timeline.
        """               
        filename = input("Enter the filename to load the timeline: ")
        if not filename.endswith('.json'):
            filename += '.json'
        full_path = os.path.abspath(os.path.join(self.dialog_save_path, filename))
        self.timeline.load(full_path)

    def save_timeline_without_prompt(self, filename, name=None, description=None):
        """
        Save the current timeline to a file without prompting for input.

        :param filename: The filename to save the timeline to.
        :param name: Optional name for the timeline session.
        :param description: Optional description for the timeline session.
        """
        if not filename.endswith('.json'):
            filename += '.json'

        full_path = os.path.join(self.dialog_save_path, filename)

        # Use provided name and description, or existing values
        if not name:
            name = getattr(self.timeline.metadata, 'name', 'Default Name')
        if not description:
            description = getattr(self.timeline.metadata, 'description', 'Default Description')

        # Save with name and description
        self.timeline.save(full_path, name=name, description=description)
        print(f"Saved timeline to '{full_path}' with name '{name}' and description '{description}'.")


    def save_timeline(self):
        """
        Save the current timeline to a file.

        Prompts the user for filename, name, and description, then saves the timeline.
        """        
        filename = input("Enter the filename to save the timeline: ")
        if not filename.endswith('.json'):
            filename += '.json'
        name = input("Enter a name for this timeline session (press enter to skip): ")
        description = input("Enter a description for this timeline session (press enter to skip): ")

        full_path = os.path.join(self.dialog_save_path, filename)

        # Check if name or description is not provided, use default or previously stored values
        if not name.strip():
            name = getattr(self.timeline, 'name', 'Default Name')  # Use existing or default name
        if not description.strip():
            description = getattr(self.timeline, 'description',
                                  'Default Description')  # Use existing or default description

        # Save with name and description
        self.timeline.save(full_path, name=name, description=description)
        print(f"Saved timeline to '{full_path}' with name '{name}' and description '{description}'.")


    def save_agent_without_prompt(self, filename, name=None, description=None):
        """
        Save the current timeline to a file without prompting for input.

        :param filename: The filename to save the timeline to.
        :param name: Optional name for the timeline session.
        :param description: Optional description for the timeline session.
        """

        # Remove extension if present
        filename_no_ext, ext = os.path.splitext(filename)

        # Python module name validation
        if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", filename_no_ext):
            raise InvalidAgentNameError(filename_no_ext)

        # File path construction
        agents_dir = os.path.expanduser("~/.underdogcowboy/agents")    
        # Create the directory if it doesn't exist
        os.makedirs(agents_dir, exist_ok=True)

        # Ensure the filename ends with '.json'
        filename = filename_no_ext + '.json'

        file_path = os.path.join(agents_dir, filename)

        # Use provided name and description, or existing values
        if not name:
            name = getattr(self.timeline.metadata, 'name', 'Default Name')
        if not description:
            description = getattr(self.timeline.metadata, 'description', 'Default Description')

        # Save with name and description
        self.timeline.save(file_path, name=name, description=description)
        # Logging or print statements as needed


    def save_agent(self):
        """Saves the current dialog as a user-defined agent."""

        agent_name = input("Enter a name for the agent: ")
        description = input("Enter a description for the agent: ")

        # Validation
        if not agent_name:
            print("Error: Agent name cannot be empty.")
            return

        # Python module name validation
        if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", agent_name):
            print("Error: Invalid agent name. Please use only letters, numbers, and underscores. The name must start with a letter or underscore.")
            return
        
        # File path construction
        agents_dir = os.path.expanduser("~/.underdogcowboy/agents")
    
        # Create the directory if it doesn't exist
        os.makedirs(agents_dir, exist_ok=True)

        file_path = os.path.join(agents_dir, f"{agent_name}.json")

        # Use the Timeline's save method
        self.timeline.save(file_path, name=agent_name, description=description)

        # Reload agents to make the new agent available
        from underdogcowboy import _reload_agents
        _reload_agents() 

        print(f"Agent saved to {file_path}")

    def head(self):
        """
        Display the current position in the timeline.

        Calls the timeline's head method to show current status.
        """        
        self.timeline.head()
    
    def display_item(self):
        """
        Display a specific item from the timeline.

        Prompts the user for an index and displays the corresponding item.
        """        
        try:
            index = int(input("Enter the index of the item to display: "))
            self.timeline.display_item(index)
        except ValueError:
            print("Invalid index.")

    # Note: The previous bug causing strange errors or timeouts when entering interactive mode
    # has likely been resolved. Two key changes address this issue:
    # 1. Requiring two consecutive Enter presses to finish input, preventing accidental empty submissions.
    # 2. Explicitly checking for empty input after stripping whitespace, ensuring only non-empty
    #    messages are sent to the LLM. These changes prevent unintended LLM calls with empty inputs,
    #    which may have been causing the observed errors or timeouts.
    def interactive_phase(self):
        """
        Enter an interactive chat session with the model.

        Allows the user to chat with the model, send files, and switch to command mode.

        Returns:
            int: The current position in the timeline after the interactive session.
        """
        def spinning_cursor():
            while loading[0]:
                for cursor in '|/-\\':
                    sys.stdout.write(f'\rModel response: {cursor}')
                    sys.stdout.flush()
                    time.sleep(0.1)
            sys.stdout.write('\r' + ' ' * 20 + '\r')
            sys.stdout.flush()

        while True:
            print("Enter your next message (press ENTER twice to finish),")
            print("'file <file_path>' to send a file, or 'cmd' to switch to command mode:")
            
            input_lines = []
            while True:
                line = input()
                if line.lower() == 'cmd':
                    return self.timeline.get_current_position()
                if line.startswith('file '):
                    input_lines = [line]
                    break
                if line == "" and not input_lines:
                    continue  # Ignore leading empty lines
                if line == "" and input_lines:
                    break
                input_lines.append(line)

            user_input = "\n".join(input_lines).strip()

            if not user_input:
                print("Empty input. Please enter a message.")
                continue

            loading = [True]
            spinner = threading.Thread(target=spinning_cursor)
            spinner.start()

            model_response, error_message = self._process_message(user_input)
            
            loading[0] = False
            spinner.join()

            if error_message:
                print(error_message)
            else:
                # print(f"[blue]{model_response}[/blue]")
                renderer.process_and_render(model_response, title="LLM Response")
                
    def _process_message(self, user_input): # used by adm
        """
        Core logic for processing a message (including file inputs) and getting a model response.
        
        Args:
            user_input (str): The user's input message or file command.
        
        Returns:
            tuple: (model_response, error_message)
        """        

        def print_conversation_to_file(conversation, filename="conversation_log.json"):
            # Write the conversation to a JSON file for easy debugging
            with open(filename, "w") as f:
                json.dump(conversation, f, indent=2)
                
        system_message = self.timeline.get_system_message()
        
        conversation = []
        if system_message:
            conversation.append({'role': 'system', 'parts': [{'text': system_message.text}]})
        
        conversation.extend([{'role': msg.role, 'parts': [{'text': msg.text}]} 
                             for msg in self.timeline.history 
                             if msg.text.strip()])

        if user_input.startswith('file '):
            file_path = user_input[5:].strip()
            file_content = self.process_file_input(file_path) 
            user_input = file_content

        user_message = self.construct_message(user_input, 'user')
        if not user_message:
            return None, "Error: Empty message not processed."

        conversation.append(user_message)
        self.timeline.add_message('user', user_input)

        # Print conversation to file for debugging
        # print_conversation_to_file(conversation, "conversation_log.json")

        try:
            model_response = self.model.generate_content(conversation)
            conversation.append(self.construct_message(model_response, 'model'))
            self.timeline.add_message('model', model_response)
            return model_response, None
        except ModelRequestException as e:
            error_message = f"Error with {e.model_type} model: {e.message}"
            if self.timeline.history[-1].role == 'user':
                self.timeline.history.pop()
            return None, error_message

    def process_single_message(self, user_input):
        """
        Process a single message (or file input) and return the model's response.

        Args:
            user_input (str): The user's input message or file command.

        Returns:
            str: The model's response or an error message.
        """
        model_response, error_message = self._process_message(user_input)
        return model_response if model_response else error_message

    def construct_message(self, message, role='user', file_path=None):
        if not message.strip():
            return None  # Return None for empty messages
        parts = [{'text': message}]
        if file_path:
            try:
                with open(file_path, 'r') as f:
                    file_content = f.read()
                if file_content.strip():
                    parts.append({'text': "\n\nFile Content:\n" + file_content})
                else:
                    parts.append({'text': "File is empty."})
            except FileNotFoundError:
                parts.append({'text': f"Error: File not found at '{file_path}'"})
            except Exception as e:
                parts.append({'text': f"Error reading file: {e}"})
        return {'role': role, 'parts': parts}

  
def  main():
    
    config_manager = LLMConfigManager()
    provider, model_name = config_manager.select_model()
    
    initial_model = ModelManager.initialize_model_with_id(provider, model_name)
    timeline = Timeline()  # Ensure timeline is correctly instantiated
    processor = CommandProcessor(timeline, initial_model)

    processor.process_command('interactive')

    while True:
        command = input("Enter a command: ").lower()
        processor.process_command(command)


if __name__ == "__main__":
    main()

