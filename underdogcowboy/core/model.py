import os
import requests
from abc import ABC, abstractmethod
from getpass import getpass
import keyring
import vertexai
from vertexai.generative_models import GenerativeModel
from groq import Groq
from .config_manager import LLMConfigManager

class ModelRequestException(Exception):
    def __init__(self, message, model_type):
        self.message = message
        self.model_type = model_type
        super().__init__(self.message)

class ConfigurableModel(ABC):
    def __init__(self, provider_type, model_id):
        self.config_manager = LLMConfigManager()
        self.config = {}
        self.provider_type = provider_type
        self.model_id = model_id

    @abstractmethod
    def initialize_model(self):
        pass

    def configure_model(self):
        print(f"Configuring {self.provider_type} provider:")
        for prop, details in self.config_manager.models[self.provider_type].items():
            if prop not in self.config or not self.config[prop]:
                if details['input_type'] == 'password':
                    value = getpass(details['question'])
                    keyring.set_password("underdogcowboy", f"{self.provider_type}_{prop}", value)
                    self.config_manager.config[self.provider_type][prop] = "KEYRING_STORED"
                else:
                    value = input(f"{details['question']} (default: {details.get('default', 'N/A')}): ")
                    if not value and 'default' in details:
                        value = details['default']
                    self.config_manager.config[self.provider_type][prop] = value

        self.config_manager.config[self.provider_type]['configured'] = True
        self.config_manager.save_config()
        print(f"{self.provider_type} provider configuration completed.")

class AnthropicModel(ConfigurableModel):
    def __init__(self, model_id):
        super().__init__("anthropic", model_id)
        self.initialize_model()

    def initialize_model(self):
        try:
            self.config = self.config_manager.get_credentials(self.provider_type)
            required_fields = ['api_key', 'api_url', 'anthropic_version']
            missing_or_empty_fields = [field for field in required_fields
                                       if field not in self.config or not self.config[field]]
            
            if missing_or_empty_fields:
                print(f"Warning: Missing or empty fields: {', '.join(missing_or_empty_fields)}")
                print(f"Starting configuration process for {self.provider_type} provider.")
                self.configure_model()
                self.config = self.config_manager.get_credentials(self.provider_type)
            
            self.api_key = self.config['api_key']
            self.api_url = self.config['api_url']
            self.anthropic_version = self.config['anthropic_version']

            self.headers = {
                "x-api-key": self.api_key,
                "content-type": "application/json",
                "anthropic-version": self.anthropic_version
            }
            print(f"{self.provider_type} provider initialized successfully for model {self.model_id}.")
        except Exception as e:
            print(f"Error initializing {self.provider_type} provider: {str(e)}")
            raise

    def generate_content(self, conversation):
        formatted_conversation = self._format_conversation(conversation)
        data = {
            "messages": formatted_conversation,
            "model": self.model_id,
            "max_tokens": 1000
        }
        
        response = requests.post(self.api_url, headers=self.headers, json=data)

        if response.status_code == 200:
            response_json = response.json()
            if 'content' in response_json and len(response_json['content']) > 0:
                return response_json['content'][0]['text']
            else:
                return "Error: Unexpected response structure"
        else:
            return f"Error: {response.status_code}, {response.text}"

    def _format_conversation(self, conversation):
        formatted_conversation = []
        for message in conversation:
            role = 'assistant' if message['role'] == 'model' else message['role']
            content = message.get('content', ' '.join(part['text'] for part in message.get('parts', []) if 'text' in part))
            if content:
                formatted_conversation.append({"role": role, "content": content})
        return formatted_conversation

class VertexAIModel(ConfigurableModel):
    def __init__(self, model_id):
        super().__init__("google-vertex", model_id)
        self.initialize_model()

    def initialize_model(self):
        try:
            self.config = self.config_manager.get_credentials(self.provider_type)
            required_fields = ['project_id', 'location', 'service_account']
            missing_or_empty_fields = [field for field in required_fields
                                       if field not in self.config or not self.config[field]]
            if missing_or_empty_fields:
                print(f"Warning: Missing or empty fields: {', '.join(missing_or_empty_fields)}")
                print(f"Starting configuration process for {self.provider_type} provider.")
                self.configure_model()
                self.config = self.config_manager.get_credentials(self.provider_type)

            self.project_id = self.config['project_id']
            self.location = self.config['location']
            self.service_account = self.config['service_account']

            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = self.service_account
            vertexai.init(project=self.project_id, location=self.location)
            self.model = GenerativeModel(self.model_id)
            print(f"{self.provider_type} provider initialized successfully for model {self.model_id}.")
        except Exception as e:
            print(f"Error initializing {self.provider_type} provider: {str(e)}")
            raise

    def generate_content(self, conversation):
        response = self.model.generate_content(conversation)
        return response.text

class GroqModel(ConfigurableModel):
    def __init__(self, model_id):
        super().__init__("groq", model_id)
        self.initialize_model()

    def initialize_model(self):
        try:
            self.config = self.config_manager.get_credentials(self.provider_type)
            
            required_fields = ['api_key']
            missing_or_empty_fields = [field for field in required_fields
                                       if field not in self.config or not self.config[field]]
            
            if missing_or_empty_fields:
                print(f"Warning: Missing or empty fields: {', '.join(missing_or_empty_fields)}")
                print(f"Starting configuration process for {self.provider_type} provider.")
                self.configure_model()
                self.config = self.config_manager.get_credentials(self.provider_type)
            
            self.api_key = self.config['api_key']
            self.client = Groq(api_key=self.api_key)
            print(f"{self.provider_type} provider initialized successfully for model {self.model_id}.")
        except Exception as e:
            print(f"Error initializing {self.provider_type} provider: {str(e)}")
            raise

    def generate_content(self, conversation):
        try:
            converted_conversation = self._convert_conversation_format(conversation)
            chat_completion = self.client.chat.completions.create(
                messages=converted_conversation,
                model=self.model_id,
            )
            return chat_completion.choices[0].message.content
        except Exception as e:
            return f"Error generating content: {str(e)}"

    def _convert_conversation_format(self, conversation):
        converted_conversation = []
        for message in conversation:
            role = 'assistant' if message['role'] == 'model' else message['role']
            content = message.get('content', ' '.join(part['text'] for part in message.get('parts', []) if 'text' in part))
            if content:
                converted_conversation.append({"role": role, "content": content})
        
        if not any(msg['role'] == 'system' for msg in converted_conversation):
            converted_conversation.insert(0, {
                "role": "system",
                "content": "You are a helpful assistant."
            })
        return converted_conversation

class ModelManager:
    @staticmethod
    def initialize_model(model_name):

        config_manager = LLMConfigManager()
        
        if model_name == 'anthropic':
            model_type = "anthropic"
            config = config_manager.get_credentials(model_type)
            model_id = config['model_id']
            return AnthropicModel(model_id)
        elif model_name == 'google-vertex':
            model_type = "google-vertex"
            config = config_manager.get_credentials(model_type)
            model_id = config['model_id']
            return VertexAIModel(model_id)
        elif model_name == 'groq':
            model_type = "groq"
            config = config_manager.get_credentials(model_type)
            model_id = config['model_id']
            return GroqModel()
        else:
            raise ValueError(f"Unsupported model: {model_name}")

    @staticmethod
    def initialize_model_with_id(provider, model_id):
        if provider == 'anthropic':
            return AnthropicModel(model_id)
        elif provider == 'google-vertex':
            return VertexAIModel(model_id)
        elif provider == 'groq':
            return GroqModel(model_id)
        else:
            raise ValueError(f"Unsupported provider: {provider}")
