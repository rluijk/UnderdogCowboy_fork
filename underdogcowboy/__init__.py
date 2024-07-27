import os
import json
import importlib.resources as pkg_resources

from .core.config_manager import LLMConfigManager
from .core.dialog_manager import DialogManager
from .core.timeline_editor import Timeline, CommandProcessor
from .core.model import ModelManager, ModelRequestException, ConfigurableModel, ClaudeAIModel, VertexAIModel
from .core.intervention import InterventionManager
from .core.extractor import JSONExtractor

class Agent:
    def __init__(self, filename, package='underdogcowboy.agents'):
        self.id = filename.split('.')[0]
        self.filename = filename
        self.package = package
        self.content = self._load_content()
    
    def _load_content(self):
        try:
            content = pkg_resources.read_text(self.package, self.filename)
            return json.loads(content)
        except FileNotFoundError:
            print(f"Agent file {self.filename} not found.")
            return None
        except Exception as e:
            print(f"Error loading agent file: {str(e)}")
            return None

def load_agents(package='underdogcowboy.agents'):
    agents = {}
    for filename in pkg_resources.contents(package):
        if filename.endswith('.json'):
            agent = Agent(filename, package)
            agents[agent.id] = agent
    return agents

# Dynamically load agents
agents = load_agents()
globals().update(agents)

__all__ = [
    'JSONExtractor', 'ClaudeAIModel', 'CommandProcessor', 'ConfigurableModel', 'DialogManager', 
    'InterventionManager', 'LLMConfigManager', 'ModelManager', 'ModelRequestException', 'Timeline', 'VertexAIModel',
    'Agent',
]

# Add dynamically loaded agents to __all__
__all__.extend(agents.keys())