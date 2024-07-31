import os
from typing import List, Type, Union, Dict, Optional, Any

from abc import ABC, abstractmethod
from .timeline_editor import Timeline, CommandProcessor
from .model import ModelManager
from .config_manager import LLMConfigManager
from .agent import Agent

class DialogManager(ABC):
    def __new__(cls, *args: Any, **kwargs: Any) -> Union['AgentDialogManager', 'BasicDialogManager']:
        if 'agent_inputs' in kwargs or (args and isinstance(args[0], (list, tuple))):
            return super().__new__(AgentDialogManager)
        else:
            return super().__new__(BasicDialogManager)

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        pass

    @abstractmethod
    def message(self, *args: Any, **kwargs: Any) -> Any:
        pass    

class BasicDialogManager(DialogManager):

    def __init__(self, model_name: Optional[str] = None) -> None:
        self.config_manager: LLMConfigManager = LLMConfigManager()
        self.dialogs: Dict[str, CommandProcessor] = {}
        self.dialog_save_path: str = self.config_manager.get_general_config().get('dialog_save_path', '')
        self.active_dialog: Optional[str] = None
        self.model_name: Optional[str] = model_name

    def load_dialog(self, filename: str) -> CommandProcessor:        
        if filename not in self.dialogs:
            if self.model_name == None:
                self.model_name = self.config_manager.select_model()

            model = ModelManager.initialize_model(self.model_name)
            timeline = Timeline()
            
            relative_path = os.path.join(self.dialog_save_path, filename)
            full_path = os.path.abspath(relative_path)
            
            if not os.path.exists(full_path):
                raise FileNotFoundError(f"Dialog file not found: {full_path}")
            
            timeline.load(full_path)
            processor = CommandProcessor(timeline, model)
            self.dialogs[filename] = processor
        
        self.active_dialog = filename
        return self.dialogs[filename]

    def message(self, processor: CommandProcessor, user_input: str) -> Any:        
        if not isinstance(processor, CommandProcessor):
            raise TypeError("Expected a CommandProcessor instance")

        self.active_dialog = next((filename for filename, proc in self.dialogs.items() if proc == processor), None)
        if self.active_dialog is None:
            raise ValueError("The provided processor is not associated with any loaded dialog")

        return processor.process_single_message(user_input)

    def get_active_processor(self) -> Optional[CommandProcessor]:    
        if self.active_dialog is None:
            return None
        return self.dialogs[self.active_dialog]

class AgentDialogManager(DialogManager):
    
    def __init__(self, agent_inputs: List[Union[Type[Agent], Agent]], model_name: Optional[str] = None, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.agents: List[Agent] = []
        self.processors: Dict[Agent, CommandProcessor] = {}
        self.active_agent: Optional[Agent] = None
        self.config_manager: LLMConfigManager = LLMConfigManager()
        self.model_name: Optional[str] = model_name        
    
        for agent_input in agent_inputs:
            if isinstance(agent_input, type) and issubclass(agent_input, Agent):
                # If it's an Agent subclass, instantiate it
                agent = agent_input(f"{agent_input.__name__}")
            elif isinstance(agent_input, Agent):
                # If it's already an Agent instance, use it directly
                agent = agent_input
            else:
                raise TypeError(f"Expected Agent subclass or instance, got {type(agent_input)}")
            
            # Register the agent with this dialog manager
            agent.register_with_dialog_manager(self)
            
            self.agents.append(agent)

    def prepare_agent(self, agent: Agent) -> CommandProcessor:
        if agent not in self.processors:
            if not hasattr(self, 'model_name') or self.model_name is None:
                self.model_name = self.config_manager.select_model()

            model = ModelManager.initialize_model(self.model_name)
            timeline = Timeline()
            
            # Use the agent's content as the initial timeline content
            timeline.load(agent.content)
            
            processor = CommandProcessor(timeline, model)
            self.processors[agent] = processor

        agent.register_with_dialog_manager(self)
        self.active_agent = agent
        return self.processors[agent]

    def message(self, agent: Agent, user_input: str) -> str:
        if not isinstance(agent, Agent):
            raise TypeError("Expected an Agent instance")

        if agent not in self.processors:
            raise ValueError("The provided agent is not prepared")

        self.active_agent = agent
        processor = self.processors[agent]
        return processor.process_single_message(user_input)

    def get_agents(self) -> List[Agent]:
        return self.agents