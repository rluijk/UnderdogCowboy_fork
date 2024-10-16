import logging
from textual.message import Message
from rich.text import Text

from underdogcowboy.core.timeline_editor import CommandProcessor

class AgentSelected(Message):
    def __init__(self, agent_name: Text):
        self.agent_name = agent_name  # Store the actual Text object
        logging.info(f"AgentSelected message created with agent_name: {self.agent_name}")
        super().__init__()

class NewAgentCreated(Message):
    def __init__(self, agent_name: str):
        self.agent_name = agent_name
        super().__init__()


class LoadAgent(Message):
    def __init__(self, agent_name: str):
        self.agent_name = agent_name
        super().__init__()
        
class AgentLoaded(Message):
    def __init__(self, processor: CommandProcessor ):
        self.processor = processor
        super().__init__()
