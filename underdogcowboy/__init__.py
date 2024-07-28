
import os
import json
from pathlib import Path 

from .core.config_manager import LLMConfigManager
from .core.dialog_manager import DialogManager
from .core.timeline_editor import Timeline, CommandProcessor
from .core.model import ModelManager, ModelRequestException, ConfigurableModel, ClaudeAIModel, VertexAIModel
from .core.intervention import InterventionManager
from .core.extractor import JSONExtractor

class Agent:
    """
    Represents an agent with associated content loaded from a JSON file.

    This class encapsulates the properties and behavior of an agent, including
    its identifier, filename, package, and content. It can load agent data
    from a JSON file and handle potential errors during the loading process.

    Attributes:
        id (str): The identifier of the agent, derived from the filename.
        filename (str): The name of the JSON file containing the agent data.
        package (str): The package or directory where the agent file is located.
        is_user_defined (bool): Indicates whether the agent is user-defined.
        content (dict): The loaded content of the agent file.
    """
    def __init__(self, filename, package, is_user_defined=False):
        self.id = os.path.splitext(filename)[0]
        self.filename = filename
        self.package = package
        self.is_user_defined = is_user_defined
        self.content = self._load_content()
    
    def _load_content(self):
        try:
            file_path = os.path.join(self.package, self.filename)
            with open(file_path, 'r') as file:
                content = file.read()
            return json.loads(content)
        except FileNotFoundError:
            print(f"Agent file {self.filename} not found.")
            return None
        except Exception as e:
            print(f"Error loading agent file: {str(e)}")
            return None

# moved to new file, less clutering in the __init__.py
from .core.specialized_agents import SPECIALIZED_AGENTS

def agent_factory(filename, package, is_user_defined=False):
    """
    Creates an appropriate Agent instance based on the filename.

    This factory function determines the type of agent to create based on the
    filename. If the agent ID (derived from the filename) matches a key in
    SPECIALIZED_AGENTS, it creates an instance of the corresponding specialized
    agent class. Otherwise, it creates a standard Agent instance.

    Args:
        filename (str): The name of the JSON file containing the agent configuration.
        package (str): The package or directory where the agent file is located.
        is_user_defined (bool, optional): Indicates whether the agent is user-defined.
            Defaults to False.

    Returns:
        Agent: An instance of either a specialized Agent subclass or the base Agent class.
    """
    agent_id = os.path.splitext(filename)[0]
    
    if agent_id in SPECIALIZED_AGENTS:
        return SPECIALIZED_AGENTS[agent_id](filename, package, is_user_defined)
    
    return Agent(filename, package, is_user_defined)

def load_agents(package='underdogcowboy.agents'):
    """
    Dynamically loads agent configurations from JSON files in the specified package and user directory.

    This function searches for JSON files in the given package directory
    and recursively in the user's .underdogcowboy/agents directory. It creates Agent instances for
    each found JSON file, with user-defined agents taking precedence over package agents.

    Args:
        package (str, optional): The base package to search for agent configurations. 
            Defaults to 'underdogcowboy.agents'.

    Returns:
        dict: A dictionary of Agent instances, keyed by their identifiers.
    """
    agents = {}
    
    def load_agents_recursive(directory, is_user_defined=False):
        """
        Recursively loads agent configurations from JSON files in the given directory.

        This inner function walks through the directory tree, creating Agent instances
        for each JSON file found. It uses the agent_factory function to create the
        appropriate type of Agent based on the filename.

        Args:
            directory (str): The directory to search for agent configuration files.
            is_user_defined (bool, optional): Indicates whether the agents in this
                directory are user-defined. Defaults to False.
        """        
        for root, _, files in os.walk(directory):
            for filename in files:
                if filename.endswith('.json'):
                    agent = agent_factory(filename, root, is_user_defined)
                    agents[agent.id] = agent
    
    # Load from package directory
    package_path = os.path.dirname(__file__)
    load_agents_recursive(package_path)
    
    # Load from user directory, overriding package agents if necessary
    user_dir = Path.home() / ".underdogcowboy" / "agents"
    if user_dir.exists():
        load_agents_recursive(str(user_dir), is_user_defined=True)
    
    return agents


# Dynamically load agents
agents = load_agents()

# Add loaded agents to the current module's namespace
for agent_id, agent in agents.items():
    globals()[agent_id] = agent

# Update __all__ to include the agent names
__all__ = [
    'JSONExtractor', 'ClaudeAIModel', 'CommandProcessor', 'ConfigurableModel', 'DialogManager', 
    'InterventionManager', 'LLMConfigManager', 'ModelManager', 'ModelRequestException', 'Timeline', 'VertexAIModel',
    'Agent',
]
__all__.extend(agents.keys())