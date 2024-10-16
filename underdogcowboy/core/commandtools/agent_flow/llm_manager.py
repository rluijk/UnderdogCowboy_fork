import logging
from underdogcowboy.core.config_manager import LLMConfigManager 

class LLMManager:
    """Handles LLM configuration and management."""

    def __init__(self, config_manager: LLMConfigManager, default_provider: str, default_model_id: str, default_model_name: str):
        self.config_manager = config_manager
        self.default_provider = default_provider
        self.default_model_id = default_model_id
        self.default_model_name = default_model_name

    def set_default_llm(self):
        """Sets the default LLM if available, or prompts the user to configure it."""
        available_models = self.config_manager.get_available_models()
        default_model_key = f"{self.default_provider}:{self.default_model_id}"

        if default_model_key in available_models:
            self.config_manager.update_model_property(self.default_provider, 'selected_model', self.default_model_id)
            logging.info(f"Default LLM set to {self.default_model_name} ({self.default_model_id})")
        else:
            logging.warning(f"Default model {self.default_model_name} is not configured.")
            self.configure_default_llm()

    def configure_default_llm(self):
        """Prompts for API credentials if the default LLM is not configured and sets the default LLM."""
        logging.info(f"Configuring default LLM: {self.default_model_name}")
        try:
            # This will prompt for the API key if not already configured
            self.config_manager.get_credentials(self.default_provider)
            # Set the selected model
            self.config_manager.update_model_property(self.default_provider, 'selected_model', self.default_model_id)
            logging.info(f"Default LLM {self.default_model_name} configured successfully")
        except Exception as e:
            logging.error(f"Failed to configure default LLM: {str(e)}")
            raise ValueError(f"Failed to configure default LLM: {str(e)}")

    def get_current_llm_config(self):
        """Retrieves the current LLM configuration."""
        try:
            return self.config_manager.get_credentials(self.default_provider)
        except Exception as e:
            logging.error(f"Failed to get current LLM config: {str(e)}")
            return None
