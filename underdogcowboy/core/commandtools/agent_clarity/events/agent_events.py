import logging
from textual.message import Message
from rich.text import Text

class AgentSelected(Message):
    def __init__(self, agent_name: Text):
        self.agent_name = agent_name  # Store the actual Text object
        logging.info(f"AgentSelected message created with agent_name: {self.agent_name}")
        super().__init__()
