import os
import json
import re

class TimelineStorage:
    def __init__(self):
        self.agents_dir = os.path.expanduser("~/.underdogcowboy/agents")
        self.dialogs_dir = os.path.expanduser("~/.underdogcowboy/dialogs")

    def save_timeline(self, data, filename, path=None):
        full_path = os.path.join(path, filename) if path else filename
        with open(full_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

    def save_new_dialog(self, name, dialog_path=None):
        path = dialog_path or self.dialogs_dir
        os.makedirs(path, exist_ok=True)
        file_path = os.path.join(path, f"{name}.json")
        data = self._create_default_data(name)
        self.save_timeline(data, file_path)

    def save_new_agent(self, agent_name):
        filename_no_ext, _ = os.path.splitext(agent_name)
        if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", filename_no_ext):
            raise ValueError("Invalid agent name")
        os.makedirs(self.agents_dir, exist_ok=True)
        file_path = os.path.join(self.agents_dir, f"{filename_no_ext}.json")
        data = self._create_default_data(filename_no_ext)
        self.save_timeline(data, file_path)

    def _create_default_data(self, name):
        return {
            "history": [],
            "metadata": {
                "frozenSegments": [],
                "startMode": 'interactive',
                "name": name,
                "description": ""
            },
            "system_message": {
                "role": "system",
                "content": ""
            }
        }
    
