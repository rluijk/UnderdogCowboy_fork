import os
from .timeline_editor import Timeline, CommandProcessor
from .model import ModelManager
from .config_manager import LLMConfigManager

class DialogManager:
    def __init__(self):
        self.config_manager = LLMConfigManager()
        self.dialogs = {}
        self.dialog_save_path = self.config_manager.get_general_config().get('dialog_save_path', '')
        self.active_dialog = None

    def load_dialog(self, filename):
        if filename not in self.dialogs:
            model_name = self.config_manager.select_model()
            model = ModelManager.initialize_model(model_name)
            timeline = Timeline()
            
            # Use os.path.join and then make it absolute
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