import os
from .timeline_editor import Timeline, CommandProcessor
from .model import ModelManager
from .config_manager import LLMConfigManager


class DialogManager:
    def __init__(self):
        self.config_manager = LLMConfigManager()
        self.dialogs = {}
        self.dialog_save_path = self.config_manager.get_general_config().get('dialog_save_path', '')

    def load_dialog(self, filename):
        if filename not in self.dialogs:
            model_name = self.config_manager.select_model()
            model = ModelManager.initialize_model(model_name)
            timeline = Timeline()
            
            # Construct the full path using the dialog_save_path
            full_path = os.path.join(self.dialog_save_path, filename)
            
            if not os.path.exists(full_path):
                raise FileNotFoundError(f"Dialog file not found: {full_path}")
            
            timeline.load(full_path)
            processor = CommandProcessor(timeline, model)
            self.dialogs[filename] = processor
        return self.dialogs[filename]

    
    def message(self, processor, user_input):
        if not isinstance(processor, CommandProcessor):
            raise TypeError("Expected a CommandProcessor instance")

        return processor.process_single_message(user_input)

'''
def agent_load_test():
    dm = DialogManager()
    try:
        agent = dm.load_dialog("agentic setup new words.json")
        return agent
    except FileNotFoundError as e:
        print(f"Error: {e}")
        return None

agent_load_test()'''