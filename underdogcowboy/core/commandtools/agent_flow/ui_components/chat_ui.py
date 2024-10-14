import logging

import os
from typing import Tuple, Union

from textual.widgets import Static
from textual.app import ComposeResult
from textual.containers import VerticalScroll

from llm_response_markdown_renderer import LLMResponseRenderer

# events
from events.dialog_events import DialogSelected
from events.agent_events import  AgentSelected

# uc
from underdogcowboy.core.config_manager import LLMConfigManager 
from underdogcowboy.core.timeline_editor import Timeline, CommandProcessor
from underdogcowboy.core.model import ModelManager, ConfigurableModel


renderer = LLMResponseRenderer(
    mdformat_config_path=None,  # Provide path if you have a custom config
)

class ChatUI(Static):

    def __init__(self,
                 name:str,
                 type=str
                 ):
        super().__init__()
        
        self.processor = None
        self.da_name = name

        if type == "dialog":
            self.load_dialog(self.da_name)
        if type == "agent":
            self.load_agent(self.da_name)    


    def compose(self) -> ComposeResult:
        with VerticalScroll(disabled=False):
            yield Static(id="chat-history")

    def on_mount(self) -> None:
        self.render_chat()


    def load_agent(self,agent_name):
        # Agent specific
        agents_dir = os.path.expanduser("~/.underdogcowboy/agents")
        agent_file = f"{agent_name}.json"

        self._load_processor(agent_file, agents_dir)

    def load_dialog(self,dialog_name):
        # Dialog specific
        config_manager: LLMConfigManager = LLMConfigManager()
        dialog_path: str = config_manager.get_general_config().get('dialog_save_path', '')

        self._load_processor(dialog_name, dialog_path)

    def _get_model_and_timeline(self) -> Tuple[ConfigurableModel, Timeline]:        
       
        self.model_id = self.app.get_current_llm_config()["model_id"]

        # TODO: Hard Coded default provider. 
        model = ModelManager.initialize_model_with_id("anthropic",self.model_id)
        
        timeline = Timeline()
        return model, timeline  

    def _load_processor(self, file_name: str, path: str) -> None:
        """General method to load a timeline and initialize the command processor."""
        try:
            self.model, self.timeline = self._get_model_and_timeline()
            self.timeline.load(file_name, path=path)
            self.processor = CommandProcessor(self.timeline, self.model)
        except FileNotFoundError:
            logging.error(f"File {file_name} not found in {path}.")
        except Exception as e:
            logging.error(f"Failed to load processor: {str(e)}")


    def render_chat(self):
        """Render chat history in the UI when available."""
        chat_history = self.processor.timeline.history
        renderable = renderer.get_renderable(chat_history, title="LLM History")
        chat_widget = self.query_one("#chat-history")
        chat_widget.update(renderable)

    def processor_updated(self, new_processor):
        """Callback triggered when the processor is updated in the app."""
        if new_processor is not None:
            history = new_processor.timeline.history
            self.render_chat(history)
        else:
            self.render_empty_chat()