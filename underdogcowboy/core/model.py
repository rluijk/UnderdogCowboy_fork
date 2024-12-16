import os
import logging
import json
import requests
import base64
from PIL import Image
import io
import re
import mimetypes

from abc import ABC, abstractmethod
from getpass import getpass
import keyring
import vertexai
from vertexai.generative_models import GenerativeModel
from groq import Groq
from .config_manager import LLMConfigManager
from .markdown_pre_processor import GoogleDocsMarkdownPreprocessor

"""
This module contains classes for different LLM (Large Language Model) providers.
Each class handles system messages differently based on the requirements of their respective APIs.

System Message Handling:

1. AnthropicModel:
   - Extracts the system message from the conversation.
   - Adds it as a separate "system" field in the API request.
   - Does not include the system message in the main message list.

2. VertexAIModel:
   - Extracts the system message from the conversation.
   - Passes it as a parameter when initializing the GenerativeModel.
   - Removes the system message from the conversation before sending to the API.

3. GroqModel:
   - Converts the conversation format, including the system message if present.
   - If no system message is found, adds a default system message at the beginning.
   - Includes the system message in the main message list sent to the API.

These differences reflect the varying requirements and structures of the underlying APIs
for each model provider. Understanding these differences is crucial when implementing
multi-model support in an application to ensure correct handling of system messages,
which often set the context or behavior for the model.
"""


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


class AnthropicModel(ConfigurableModel):

    def __init__(self, model_id):
        super().__init__("anthropic", model_id)
        self.model_id = model_id  # Make sure this is just the model string, e.g., "claude-3-5-sonnet-20240620"
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
                # self.configure_model()
                self.config = self.config_manager.get_credentials(self.provider_type)
            
            self.api_key = self.config['api_key']
            self.api_url = self.config['api_url']
            self.anthropic_version = self.config['anthropic_version']

            #logging.info(f"api key test: {self.api_key}")


            self.headers = {
                "x-api-key": self.api_key,
                "content-type": "application/json",
                "anthropic-version": self.anthropic_version
            }
            print(f"{self.provider_type} provider initialized successfully for model {self.model_id}.")
        except Exception as e:
            print(f"Error initializing {self.provider_type} provider: {str(e)}")
            raise

    def _encode_image(self, image_path):
        mime_type, _ = mimetypes.guess_type(image_path)
        if mime_type not in ['image/jpeg', 'image/png', 'image/gif', 'image/webp']:
            raise ValueError(f"Unsupported image format: {mime_type}")

        with open(image_path, 'rb') as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')

    def create_conversation_structure(self, input_text):
        NORMAL, IMAGE_PATH, BASE64 = 0, 1, 2
        state = NORMAL
        text_buffer = ''
        image_buffer = ''
        valid_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}
        output = {'role': 'user', 'parts': []}
        length = len(input_text)
        i = 0

        def add_text_part():
            text = ' '.join(text_buffer.split()).strip()
            if text:
                output['parts'].append({'text': text})
            text_buffer = ''

        def add_image_part(image_data):
            image_data = image_data.strip()
            if image_data.startswith('data:image/'):
                # Base64 image
                mime_type = image_data.split(';')[0].split(':')[1]
                base64_data = image_data.split(',')[1]
                output['parts'].append({
                    'image': {
                        'type': 'base64',
                        'media_type': mime_type,
                        'data': base64_data
                    }
                })
            else:
                # File path
                output['parts'].append({'image_url': {'url': image_data}})

        while i < length:
            char = input_text[i]
            if state == NORMAL:
                if char == '/':
                    if text_buffer:
                        add_text_part()
                    image_buffer = char
                    state = IMAGE_PATH
                elif input_text[i:].startswith('data:image/'):
                    if text_buffer:
                        add_text_part()
                    image_buffer = ''
                    state = BASE64
                else:
                    text_buffer += char
            elif state == IMAGE_PATH:
                if char.isspace() or i == length - 1:
                    if i == length - 1 and not char.isspace():
                        image_buffer += char
                    # Trim any whitespace characters
                    image_buffer = image_buffer.strip()
                    if any(image_buffer.lower().endswith(ext) for ext in valid_extensions):
                        add_image_part(image_buffer)
                    else:
                        text_buffer += image_buffer + char
                    image_buffer = ''
                    state = NORMAL
                else:
                    image_buffer += char
            elif state == BASE64:
                end_index = input_text.find(' ', i)
                if end_index == -1:
                    end_index = length
                image_buffer = input_text[i:end_index]
                add_image_part('data:image/' + image_buffer)
                i = end_index - 1
                state = NORMAL
            i += 1

        if state == IMAGE_PATH and image_buffer:
            image_buffer = image_buffer.strip()
            if any(image_buffer.lower().endswith(ext) for ext in valid_extensions):
                add_image_part(image_buffer)
            else:
                text_buffer += image_buffer
        elif text_buffer:
            add_text_part()

        return [output]

    def generate_content(self, conversation):
        system_message = None
        formatted_conversation = []

        # Regular expression to find file paths in text
        image_path_pattern = r'(/[\w\-/\. ]+\.(png|jpg|jpeg|gif|bmp))'
        # Instantiate the preprocessor
        # preprocessor = GoogleDocsMarkdownPreprocessor()

        for message in conversation:
            role = message['role']
            if role == 'model':
                role = 'assistant'

            # Extract system message
            if role == 'system':
                system_message = message['parts'][0]['text'] if 'parts' in message else message.get('content', '')
                continue

            content = []

            if 'parts' in message:
                for part in message['parts']:
                    # Check for text content
                    if 'text' in part:
                        text = part['text']
                        content.append({"type": "text", "text": text})

                        # Parse and extract image paths from text
                        image_paths = re.findall(image_path_pattern, text)
                        for path, _ in image_paths:
                            try:
                                mime_type, _ = mimetypes.guess_type(path)
                                image_data = self._encode_image(path)  # May raise FileNotFoundError or similar
                                content.append({
                                    "type": "image",
                                    "source": {
                                        "type": "base64",
                                        "media_type": mime_type,
                                        "data": image_data
                                    }
                                })
                            except FileNotFoundError:
                                # Example or placeholder paths may reference non-existent images.
                                # In such cases, we skip these entries gracefully to ensure the
                                # overall process continues without interruption or unnecessary warnings.
                                logging.warning(f"Image file not found, skipping: {path}")
                            except Exception as e:
                                # Log unexpected errors for debugging while continuing with other images.
                                # This ensures robust processing and avoids halting due to unforeseen issues.
                                logging.error(f"Unexpected error while processing image {path}: {e}")

                    # Check for image URL
                    elif 'image_url' in part and 'url' in part['image_url']:
                        image_path = part['image_url']['url']
                        mime_type, _ = mimetypes.guess_type(image_path)
                        image_data = self._encode_image(image_path)
                        content.append({
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": mime_type,
                                "data": image_data
                            }
                        })
                    # Check for already embedded image data
                    elif 'image' in part:
                        content.append({
                            "type": "image",
                            "source": part['image']
                        })

            elif 'content' in message:
                for item in message['content']:
                    if isinstance(item, dict):
                        if item['type'] == 'text':
                            content.append({"type": "text", "text": item['text']})
                        elif item['type'] == 'image':
                            content.append(item)
                    else:
                        content.append({"type": "text", "text": item})

            # Add the formatted message to the conversation
            formatted_conversation.append({
                "role": role,
                "content": content
            })

        # Prepare data for the API request
        data = {
            "model": self.model_id,
            "messages": formatted_conversation,
            "max_tokens": 4500
        }

        if system_message:
            data["system"] = system_message

        logging.debug("Entering request to Anthropic API")
        response = requests.post(self.api_url, headers=self.headers, json=data)
        logging.debug("Response received from Anthropic API")

        if response.status_code == 200:
            response_json = response.json()
            if 'content' in response_json and len(response_json['content']) > 0:
                return response_json['content'][0]['text']
            else:
                return "Error: Unexpected response structure"
        else:
            return f"Error: {response.status_code}, {response.text}"


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
                # self.configure_model()
                self.config = self.config_manager.get_credentials(self.provider_type)

            self.project_id = self.config['project_id']
            self.location = self.config['location']
            self.service_account = self.config['service_account']

            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = self.service_account
            vertexai.init(project=self.project_id, location=self.location)
            self.model = None # GenerativeModel(self.model_id)
            print(f"{self.provider_type} provider initialized successfully for model {self.model_id}.")
        except Exception as e:
            print(f"Error initializing {self.provider_type} provider: {str(e)}")
            raise

    def _encode_image(self, image_path):
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')

    def generate_content(self, conversation):
        
        # we pass the system instruction as a property next to the model
        # name, when making the model.
        system_instruction = []
        for message in conversation:
            if message['role'] == 'system':
                system_instruction.append(message['parts'][0]['text'])
                break

        # the conversation can not contain the system message, so we filter it out.                
        filtered_conversation = [msg for msg in conversation if msg['role'] != 'system']
                
        # Create a new GenerativeModel instance with the extracted system instruction
        self.model = GenerativeModel(
            model_name=self.model_id,  # Use self.model_id instead of hardcoding
            system_instruction=system_instruction if system_instruction else [],  # Provide system instruction if found
        )

        response = self.model.generate_content(filtered_conversation)
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
                # self.configure_model()
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

class XAIModel(ConfigurableModel):
    def __init__(self, model_id):
        super().__init__("grok", model_id)
        self.initialize_model()

    def initialize_model(self):
        try:
            self.config = self.config_manager.get_credentials(self.provider_type)
            
            # Check for required configuration fields
            required_fields = ['api_key', 'base_url']
            missing_or_empty_fields = [field for field in required_fields
                                       if field not in self.config or not self.config[field]]
            
            if missing_or_empty_fields:
                logging.warning(f"Warning: Missing or empty fields: {', '.join(missing_or_empty_fields)}")
                logging.warning(f"Starting configuration process for {self.provider_type} provider.")
                self.config = self.config_manager.get_credentials(self.provider_type)
            
            self.api_key = self.config['api_key']
            self.base_url = "https://api.x.ai/v1/chat/completions"

            self.headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}" 
            }

        except Exception as e:
            logging.error(f"Error initializing {self.provider_type} provider: {str(e)}")
            raise

    def generate_content(self, conversation):
        system_message = None
        formatted_conversation = []

        for message in conversation:
            role = message['role']
            if role == 'model':
                role = 'assistant'

            # Extract system message
            if role == 'system':
                system_message = message['parts'][0]['text'] if 'parts' in message else message.get('content', '')
                continue

            content = []

            if 'parts' in message:
                for part in message['parts']:
                    # Check for text content only
                    if 'text' in part:
                        text = part['text']
                        content.append({"type": "text", "text": text})

            elif 'content' in message:
                for item in message['content']:
                    if isinstance(item, dict) and item['type'] == 'text':
                        content.append({"type": "text", "text": item['text']})
                    elif isinstance(item, str):
                        content.append({"type": "text", "text": item})

            # Add the formatted message to the conversation
            formatted_conversation.append({
                "role": role,
                "content": content
            })

        # Prepare data for the API request
        data = {
            "model": self.model_id,
            "messages": formatted_conversation,
            "temperature": 0
        }

        if system_message:
            data["system"] = system_message

        response = requests.post(self.base_url, headers=self.headers, json=data)

        if response.status_code == 200:
            response_json = response.json()
            # Access 'choices' list and retrieve 'content' under 'message'
            if 'choices' in response_json and len(response_json['choices']) > 0:
                message_content = response_json['choices'][0].get('message', {}).get('content')
                if message_content:
                    return message_content
                else:
                    return "Error: Unexpected response structure - 'message.content' missing"
            else:
                return "Error: Unexpected response structure - 'choices' missing or empty"
        else:
            return f"Error: {response.status_code}, {response.text}"


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
            return GroqModel(model_id)
        elif model_name == 'grok':
            model_type = "grok"
            config = config_manager.get_credentials(model_type)
            model_id = config['model_id']
            return XAIModel(model_id)
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
        elif provider == 'grok':
            return XAIModel(model_id)
        else:
            raise ValueError(f"Unsupported provider: {provider}")
