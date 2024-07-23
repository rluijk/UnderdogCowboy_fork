import os
import requests

from abc import ABC, abstractmethod

from getpass import getpass
import keyring

import vertexai
from vertexai.generative_models import GenerativeModel

from .config_manager import LLMConfigManager


class ModelRequestException(Exception):
    def __init__(self, message, model_type):
        self.message = message
        self.model_type = model_type
        super().__init__(self.message)


class ConfigurableModel(ABC):
    """
    An abstract base class for configurable AI models.

    This class provides a framework for AI models that require configuration
    before use. It includes methods for initializing the model and configuring
    its parameters.

    Attributes:
        config_manager (LLMConfigManager): An instance of LLMConfigManager used to manage
            configuration settings.
        config (dict): A dictionary to store the configuration settings for the model.
        model_type (str): A string identifier for the type of model. This should be set
            by subclasses.

    Note:
        Subclasses should set the `model_type` attribute in their __init__ method.
    """

    def __init__(self):
        """
        Initialize the ConfigurableModel.

        Sets up the config_manager, an empty config dictionary, and a placeholder
        for model_type.
        """
        self.config_manager = LLMConfigManager()
        self.config = {}
        self.model_type = ""  # To be set by subclasses

    @abstractmethod
    def initialize_model(self):
        """
        Initialize the model.

        This method should be implemented by subclasses to perform any necessary
        setup or initialization for the specific model type.

        Raises:
            NotImplementedError: If the subclass does not implement this method.
        """
        pass

    def configure_model(self):
        """
        Configure the model based on the configuration settings.

        This method interactively prompts the user for configuration details
        if they are not already set. It handles both regular input and password
        input, storing passwords securely using the keyring library.

        The method performs the following steps:
        1. Iterates through the configuration properties for the model type.
        2. For each property not set, prompts the user for input.
        3. For password fields, uses getpass for secure input and stores in keyring.
        4. For non-password fields, uses regular input and stores the value directly.
        5. Uses default values if provided and the user input is empty.
        6. Saves the updated configuration.

        Note:
            This method assumes that `self.model_type` has been set by the subclass.

        Raises:
            KeyError: If the model type is not properly set or recognized.
        """
        print(f"Configuring {self.model_type} model:")
        for prop, details in self.config_manager.models[self.model_type].items():
            if prop not in self.config or not self.config[prop]:
                if details['input_type'] == 'password':
                    value = getpass(details['question'])
                    keyring.set_password("underdogcowboy", f"{self.model_type}_{prop}", value)
                    self.config_manager.config[self.model_type][prop] = "KEYRING_STORED"
                else:
                    value = input(f"{details['question']} (default: {details.get('default', 'N/A')}): ")
                    if not value and 'default' in details:
                        value = details['default']
                    self.config_manager.config[self.model_type][prop] = value

        self.config_manager.config[self.model_type]['configured'] = True
        self.config_manager.save_config()
        print(f"{self.model_type} model configuration completed.")
    
class ClaudeAIModel(ConfigurableModel):

    def __init__(self):
        """
        Initialize the ClaudeAIModel.

        This method sets up the model type and calls the initialize_model method
        to set up the Claude AI model.
        """
        super().__init__()
        self.model_type = "anthropic"
        self.initialize_model()    

    def initialize_model(self):
        """
        Initialize the Claude AI model.

        This method performs the following steps:
        1. Retrieves the model credentials.
        2. Checks for missing or empty required fields.
        3. Configures the model if necessary.
        4. Sets up the Claude AI environment.
        
        If any required fields are missing, it will prompt the user to configure them.

        Raises:
            Exception: If there's an error during the initialization process.
                The specific exception is caught, logged, and re-raised.
        """
        try:
            self.config = self.config_manager.get_credentials(self.model_type)
            
            required_fields = ['api_key', 'model_id', 'api_url', 'anthropic_version']
            missing_or_empty_fields = [field for field in required_fields
                                       if field not in self.config or not self.config[field]]
            
            if missing_or_empty_fields:
                print(f"Warning: Missing or empty fields: {', '.join(missing_or_empty_fields)}")
                print(f"Starting configuration process for {self.model_type} model.")
                self.configure_model()
                # After setup, try to get the credentials again
                self.config = self.config_manager.get_credentials(self.model_type)
            
            self.api_key = self.config['api_key']
            self.model_id = self.config['model_id']
            self.api_url = self.config['api_url']
            self.anthropic_version = self.config['anthropic_version']

            self.headers = {
                "x-api-key": self.api_key,
                "content-type": "application/json",
                "anthropic-version": self.anthropic_version
            }
            self.model = None  # Claude doesn't require a model object to be instantiated
            print(f"{self.model_type} model initialized successfully.")
        except Exception as e:
            print(f"Error initializing {self.model_type} model: {str(e)}")
            print(f"Please ensure you have provided all required information for the {self.model_type} model.")
            raise           

    def generate_content(self, conversation):
        """
        Generate content using the Claude AI model.

        This method takes a conversation history, formats it appropriately for the Claude API,
        and uses the model to generate a response.

        Args:
            conversation (list): A list of dictionaries representing the 
                conversation history. Each dictionary should contain 
                'role' and 'content' keys.

        Returns:
            str: The generated response text, or an error message if the request fails.

        Note:
            This method performs the following steps:
            1. Formats the conversation history for the Claude API.
            2. Sends a POST request to the Claude API.
            3. Processes the API response to extract the generated content.
            4. Returns the generated text or an error message.

        Raises:
            Potential HTTP exceptions from the requests library are caught and
            returned as error messages in the response string.
        """
        # Ensure the conversation has the correct structure
        formatted_conversation = []
        for message in conversation:
            role = message['role']
            if role == 'model':
                role = 'assistant'  # Convert 'model' role to 'assistant'
            
            if 'parts' in message:
                # Convert 'parts' structure to 'content'
                content = ' '.join(part['text'] for part in message['parts'] if 'text' in part)
            elif 'content' in message:
                content = message['content']
            else:
                continue  # Skip messages without content

            formatted_conversation.append({
                "role": role,
                "content": content
            })
        
        data = {
            "messages": formatted_conversation,
            "model": self.model_id,
            "max_tokens": 1000
        }
        
        response = requests.post(self.api_url, headers=self.headers, json=data)
        
        if response.status_code == 200:
            response_json = response.json()
            if 'content' in response_json and len(response_json['content']) > 0:
                assistant_message = response_json['content'][0]['text']
                return assistant_message
            else:
                return "Error: Unexpected response structure"
        else:
            return f"Error: {response.status_code}, {response.text}"

class VertexAIModel(ConfigurableModel):
    def __init__(self):
        """
        Initialize the VertexAIModel.

        This method sets up the model type and calls the initialize_model method
        to set up the Vertex AI model.
        """
        super().__init__()
        self.model_type = "google-vertex"
        self.initialize_model()

    def initialize_model(self):
        """
        Initialize the Vertex AI model.

        This method performs the following steps:
        1. Retrieves the model credentials.
        2. Checks for missing or empty required fields.
        3. Configures the model if necessary.
        4. Sets up the Vertex AI environment.
        5. Initializes the GenerativeModel.

        If any required fields are missing, it will prompt the user to configure them.

        Raises:
            Exception: If there's an error during the initialization process.
                The specific exception is caught, logged, and re-raised.
        """
        try:
            self.config = self.config_manager.get_credentials(self.model_type)
            required_fields = ['project_id', 'location', 'model_id', 'service_account']
            missing_or_empty_fields = [field for field in required_fields
                                       if field not in self.config or not self.config[field]]
            if missing_or_empty_fields:
                print(f"Warning: Missing or empty fields: {', '.join(missing_or_empty_fields)}")
                print(f"Starting configuration process for {self.model_type} model.")
                self.configure_model()
                # After setup, try to get the credentials again
                self.config = self.config_manager.get_credentials(self.model_type)

            self.project_id = self.config['project_id']
            self.location = self.config['location']
            self.model_id = self.config['model_id']
            self.service_account = self.config['service_account']

            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = self.service_account
            vertexai.init(project=self.project_id, location=self.location)
            self.model = GenerativeModel(self.model_id)
            print(f"{self.model_type} model initialized successfully.")
        except Exception as e:
            print(f"Error initializing {self.model_type} model: {str(e)}")
            print(f"Please ensure you have provided all required information for the {self.model_type} model.")
            raise

    def generate_content(self, conversation):
        """
        Generate content using the Vertex AI model.

        This method takes a conversation history and uses the Vertex AI
        model to generate a response.

        Args:
            conversation (list): A list of dictionaries representing the 
                conversation history. Each dictionary should contain 
                'role' and 'content' keys.

        Returns:
            str: The generated response text.

        Note:
            The specific format of the 'conversation' parameter may depend
            on the requirements of the Vertex AI model being used.
        """        
        response = self.model.generate_content(conversation)
        return response.text

class ModelManager:
    """
    A utility class for managing and initializing different AI models.

    This class provides static methods to determine the execution environment
    and initialize specific AI models based on the given model name.

    Methods:
    
        initialize_model(model_name: str) -> SubClass of ConfigurableModel:
            Initializes and returns an instance of the specified AI model.

    Usage:
        model_manager = ModelManager()
        claude_model = model_manager.initialize_model('anthropic')
        vertex_model = model_manager.initialize_model('google-vertex')

    Note:
        This class assumes that the necessary model classes (e.g., ClaudeAIModel, 
        VertexAIModel) are defined and available in the same scope.
    """
    
    @staticmethod
    def initialize_model(model_name):
        
        if model_name == 'anthropic':
            return ClaudeAIModel()
        elif model_name == 'google-vertex':
            return VertexAIModel()
        else:
            raise ValueError(f"Unsupported model: {model_name}")
        