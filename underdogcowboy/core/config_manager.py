import json
from pathlib import Path
from getpass import getpass
import keyring

class LLMConfigManager:
    """
    A class for managing configurations for various Language Learning Models (LLMs).

    This class handles loading, saving, and retrieving credentials for different LLM providers.
    It also provides functionality to select a model from available options.
    """
    def __init__(self):
        """
        Initialize the LLMConfigManager.

        Sets up the configuration file path and loads existing configurations.
        Also defines the structure for different LLM models and their required credentials.
        """
        self.config_file = Path.home() / '.underdogcowboy' / 'config.json'
        self.config = self.load_config()
        self.models = {
            'anthropic': {
                'api_key': {'question': 'Enter your Anthropic API key:', 'input_type': 'password'},
                'model_id': {'question': 'Enter the Anthropic model ID:', 'input_type': 'text', 'default': 'claude-3-sonnet-20240229'},
                'api_url': {'question': 'Enter the Anthropic API URL:', 'input_type': 'text', 'default': 'https://api.anthropic.com/v1/messages'},
                'anthropic_version': {'question': 'Enter the Anthropic API version:', 'input_type': 'text', 'default': '2023-06-01'}
            },
            'google-vertex': {
                'service_account': {'question': 'Enter the path to your Google service account JSON file:', 'input_type': 'file'},
                'project_id': {'question': 'Enter the project id from your google cloud configuration', 'input_type': 'text' },
                'location': {'question': 'Enter the location from your google cloud configuration', 'input_type': 'text', 'default': 'us-central1' },
                'model_id': {'question': 'Enter the model name (id from google LLM)', 'input_type': 'text', 'default': 'gemini-1.5-pro-preview-0514' }
            }
        }
        self.general_config = {
            'dialog_save_path': {'question': 'Enter the path to save dialogs:', 'input_type': 'path', 'default': str(Path.home() / 'llm_dialogs')},
            'message_export_path': {'question': 'Enter the path to export messages:', 'input_type': 'path', 'default': str(Path.home() / 'llm_exports')}
        }

    def load_config(self):
        """
        Load the configuration from the JSON file.

        Returns:
            dict: The loaded configuration, or an empty dictionary if the file doesn't exist.
        """
        if self.config_file.exists():
            with open(self.config_file, 'r') as f:
                return json.load(f)
        return {}

    def save_config(self):
        """
        Save the current configuration to the JSON file.

        This method ensures that sensitive information (like API keys) is not stored directly in the file.
        Instead, it marks such information as "KEYRING_STORED" in the saved config.
        """        
        safe_config = self.config.copy()
        for model in safe_config:
            for prop, details in self.models.get(model, {}).items():
                if details.get('input_type') == 'password':
                    safe_config[model][prop] = "KEYRING_STORED"
        
        self.config_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_file, 'w') as f:
            json.dump(safe_config, f)
    
    def get_credentials(self, model):
        """
        Retrieve or prompt for credentials for a specific model.

        If credentials are not already stored, this method will prompt the user to enter them.
        Sensitive information is stored securely using the keyring module.

        Args:
            model (str): The name of the model to get credentials for.

        Returns:
            dict: A dictionary containing the credentials for the specified model.
        """
        if model not in self.config or not self.config[model].get('configured', False):
            print(f"No stored credentials found for {model}. Please enter them now.")
            self.config[model] = {}
            for prop, details in self.models[model].items():
                if details['input_type'] == 'password':
                    value = getpass(details['question'])
                    keyring.set_password("underdogcowboy", f"{model}_{prop}", value)
                    # Don't store the password in the JSON config
                    self.config[model][prop] = "KEYRING_STORED"
                else:
                    value = input(f"{details['question']} (default: {details.get('default', 'N/A')}): ")
                    if not value and 'default' in details:
                        value = details['default']
                    self.config[model][prop] = value
            self.config[model]['configured'] = True
            self.save_config()

        credentials = {}
        for prop, details in self.models[model].items():
            if details['input_type'] == 'password':
                value = keyring.get_password("underdogcowboy", f"{model}_{prop}")
            else:
                value = self.config[model].get(prop)
            if not value and 'default' in details:
                value = details['default']
            credentials[prop] = value
        return credentials

    def get_general_config(self):
        """
        Retrieve or prompt for general configuration settings.

        If settings are not already stored, this method will prompt the user to enter them.

        Returns:
            dict: A dictionary containing the general configuration settings.
        """
        if 'general' not in self.config or not self.config['general'].get('configured', False):
            print("No stored general configuration found. Please enter them now.")
            self.config['general'] = {}
            for prop, details in self.general_config.items():
                value = input(f"{details['question']} (default: {details.get('default', 'N/A')}): ")
                if not value and 'default' in details:
                    value = details['default']
                self.config['general'][prop] = value
            self.config['general']['configured'] = True
            self.save_config()

        return {prop: self.config['general'].get(prop, details.get('default')) 
                for prop, details in self.general_config.items()}

    def update_general_config(self):
        """
        Update the general configuration settings.

        This method allows the user to update the dialog save path and message export path.
        """
        print("Updating general configuration settings:")
        for prop, details in self.general_config.items():
            current_value = self.config['general'].get(prop, details.get('default', 'N/A'))
            value = input(f"{details['question']} (current: {current_value}, press Enter to keep current): ")
            if value:
                self.config['general'][prop] = value
        self.save_config()
        print("General configuration updated successfully.")

    def select_model(self):
        """
        Prompt the user to select a model from the available options.

        This method displays a numbered list of available models and asks the user to choose one.

        Returns:
            str: The name of the selected model.

        Raises:
            ValueError: If the user enters an invalid input.
        """        
        print("Available models:")
        for i, model in enumerate(self.models.keys(), 1):
            print(f"{i}. {model}")
        
        while True:
            try:
                choice = int(input("Select a model (enter the number): "))
                if 1 <= choice <= len(self.models):
                    return list(self.models.keys())[choice - 1]
                else:
                    print("Invalid choice. Please try again.")
            except ValueError:
                print("Please enter a valid number.")

    def get_available_models(self):
        return sorted(self.models.keys())