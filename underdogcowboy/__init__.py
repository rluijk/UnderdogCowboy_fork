"""
Underdog Cowboy Agent System Initialization

This __init__.py file serves as the entry point for the Underdog Cowboy agent system.
It provides dynamic loading and initialization of various agent types, including
both pre-defined and user-defined agents.

Key components:
- Agent class: Represents an agent with associated content loaded from a JSON file.
- agent_factory: Creates appropriate Agent instances based on the filename.
- load_agents: Dynamically loads agent configurations from JSON files.
- Specialized agents: Imported from core.specialized_agents.

The module performs the following actions:
1. Imports necessary modules and components.
2. Defines the Agent class and related functions.
3. Dynamically loads agents from both the package directory and user directory.
4. Adds loaded agents to the current module's namespace.
5. Updates __all__ to include core components and dynamically loaded agent names.

This structure allows for easy extension of the agent system, supporting both
built-in agents and user-defined agents. User-defined agents take precedence
over package agents with the same identifier.

Note: 
The actual agent instances are dynamically added to this module's namespace,
allowing direct access to them after import.
"""
print('Pre Release -- Early Access Version... Nov-Dec 2024')
print('If you do not have my Whatsapp, DM on linked-in for issues that need solving: https://www.linkedin.com/in/reneluijk/')
import warnings



import logging

# Step 1: Remove all handlers from the root logger
root_logger = logging.getLogger()
if root_logger.hasHandlers():
    root_logger.handlers.clear()

# Step 2: Create and configure your custom logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)

file_handler = logging.FileHandler('file.log')
file_handler.setLevel(logging.WARNING)

formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)

logger.addHandler(file_handler)
logger.propagate = False

# Step 3: Suppress logging from third-party libraries
third_party_loggers = [
    'urllib3',
    'google.cloud.storage',
    'keyring.backend',
    # Add more logger names as needed
]

for lib_logger in third_party_loggers:
    logging.getLogger(lib_logger).setLevel(logging.ERROR)

import os
import json
from pathlib import Path 

logger.debug("Basic imports completed")

from .core.config_manager import LLMConfigManager
from .core.dialog_manager import DialogManager, AgentDialogManager
from .core.timeline_editor import Timeline, CommandProcessor
from .core.model import ModelManager, ModelRequestException, ConfigurableModel, VertexAIModel, AnthropicModel, GroqModel
from .core.intervention import InterventionManager
from .core.extractor import JSONExtractor
from .core.agent import Agent
from .core.markdown_pre_processor import MarkdownPreprocessor, GoogleDocsMarkdownPreprocessor
from .core.uc_agent_communicator import UCAgentCommunicator
from .core.llm_response_markdown import LLMResponseRenderer       

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
    logger.debug(f"Creating agent for {filename}")
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
    logger.debug(f"Loading agents from package: {package}")
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


def _reload_agents(package='underdogcowboy.agents'):
    """Reloads agents and updates global variables."""
    global agents, __all__
    agents = load_agents(package)
    __all__.extend(agents.keys())

# Dynamically load agents
logger.debug("About to load agents")
agents = load_agents()
logger.debug(f"Loaded {len(agents)} agents")

# Add loaded agents to the current module's namespace
logger.debug("Adding agents to namespace")
for agent_id, agent in agents.items():
    logger.debug(f"Adding agent {agent_id} to namespace")
    try:
        globals()[agent_id] = agent
        logger.debug(f"Successfully added {agent_id}")
    except Exception as e:
        logger.error(f"Error adding agent {agent_id} to namespace: {str(e)}")
        import traceback
        traceback.print_exc()

logger.debug("Finished adding agents to namespace")


# Create an instance of AgentDialogManager
agent_dialog_manager = AgentDialogManager([])
# Add it to the global namespace
globals()['adm'] = agent_dialog_manager

# Update __all__ to include the agent names
logger.debug("Updating __all__")
__all__ = [
    'JSONExtractor', 'CommandProcessor', 'ConfigurableModel', 'DialogManager', 'AgentDialogManager', 
    'InterventionManager', 'LLMConfigManager', 'ModelManager', 'ModelRequestException', 'Timeline',
    'Agent', 'adm','MarkdownPreprocessor','GoogleDocsMarkdownPreprocessor'
    'Response','VertexAIModel', 'AnthropicModel', 'GroqModel','UCAgentCommunicator', 'LLMResponseRenderer',
]
__all__.extend(agents.keys())
logger.debug("Finished updating __all__")

logger.debug("__init__.py execution completed")
