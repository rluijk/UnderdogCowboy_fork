import os
from .timeline_editor import Timeline, CommandProcessor
from .model import ModelManager
from .config_manager import LLMConfigManager
from .agent import Agent

class DialogManager:
    def __new__(cls, *args, **kwargs):
        if 'agent_inputs' in kwargs or (args and isinstance(args[0], (list, tuple))):
            return super().__new__(AgentDialogManager)
        else:
            return super().__new__(BasicDialogManager)

    def __init__(self, *args, **kwargs):
        pass

class BasicDialogManager(DialogManager):
    def __init__(self,model_name=None):
        self.config_manager = LLMConfigManager()
        self.dialogs = {}
        self.dialog_save_path = self.config_manager.get_general_config().get('dialog_save_path', '')
        self.active_dialog = None
        self.model_name = model_name

    def load_dialog(self, filename):
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

    def message(self, processor, user_input):
        if not isinstance(processor, CommandProcessor):
            raise TypeError("Expected a CommandProcessor instance")

        self.active_dialog = next((filename for filename, proc in self.dialogs.items() if proc == processor), None)
        if self.active_dialog is None:
            raise ValueError("The provided processor is not associated with any loaded dialog")

        return processor.process_single_message(user_input)

    def get_active_processor(self):
        if self.active_dialog is None:
            return None
        return self.dialogs[self.active_dialog]

class AgentDialogManager(DialogManager):
    def __init__(self, agent_inputs,  **kwargs):
        super().__init__()
        self.agents = []
        for agent_input in agent_inputs:
            if isinstance(agent_input, type) and issubclass(agent_input, Agent):
                # If it's an Agent subclass, instantiate it
                agent = agent_input(f"{agent_input.__name__}")
            elif isinstance(agent_input, Agent):
                # If it's already an Agent instance, use it directly
                agent = agent_input
            else:
                raise TypeError(f"Expected Agent subclass or instance, got {type(agent_input)}")
            self.agents.append(agent)

    def get_agents(self):
        return self.agents