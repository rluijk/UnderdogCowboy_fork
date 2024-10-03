import json
from datetime import datetime
from typing import Any, Dict, List

from .shared_data import SessionData, ScreenData, SharedData

class SharedStorage:
    def __init__(self, session_data: SessionData = None):
        if session_data:
            self.session_data = session_data
        else:
            self.session_data = SessionData()

    def update_data(self, key: str, value: Any, screen_name: str = None) -> None:
        if screen_name:
            # Update screen-specific data
            if screen_name not in self.session_data.screens:
                self.session_data.screens[screen_name] = ScreenData()
            self.session_data.screens[screen_name].data[key] = value
        else:
            # Update shared data
            self.session_data.shared_data.data[key] = value
    def get_data(self, key: str, screen_name: str = None) -> Any:
        if screen_name:
            # Get screen-specific data
            screen_data = self.session_data.screens.get(screen_name)
            if screen_data:
                return screen_data.data.get(key)
            else:
                return None
        else:
            # Get shared data
            return self.session_data.shared_data.data.get(key)
    def add_command_result(self, command: str, result: Any, screen_name: str = None) -> None:
        command_entry = {
            "command": command,
            "result": result,
            "timestamp": datetime.now().isoformat()
        }
        if screen_name:
            # Add to screen-specific command history
            if screen_name not in self.session_data.screens:
                self.session_data.screens[screen_name] = ScreenData()
            self.session_data.screens[screen_name].command_history.append(command_entry)
        else:
            # Add to shared command history
            self.session_data.shared_data.command_history.append(command_entry)

    def to_json(self) -> str:
        # Convert session_data to a serializable dictionary
        def serialize_session_data(session_data: SessionData) -> Dict[str, Any]:
            return {
                "shared_data": {
                    "version": session_data.shared_data.version,
                    "data": session_data.shared_data.data,
                    "command_history": session_data.shared_data.command_history,
                },
                "screens": {
                    screen_name: {
                        "data": screen_data.data,
                        "command_history": screen_data.command_history
                    } for screen_name, screen_data in session_data.screens.items()
                }
            }
        session_dict = serialize_session_data(self.session_data)
        return json.dumps(session_dict, default=str, indent=2)

    @classmethod
    def from_json(cls, json_str: str) -> 'SharedStorage':
        data = json.loads(json_str)
        # Reconstruct SessionData from the dictionary
        shared_data = SharedData(
            version=data["shared_data"]["version"],
            data=data["shared_data"]["data"],
            command_history=data["shared_data"]["command_history"]
        )
        screens = {}
        for screen_name, screen_info in data.get("screens", {}).items():
            screens[screen_name] = ScreenData(
                data=screen_info["data"],
                command_history=screen_info["command_history"]
            )
        session_data = SessionData(shared_data=shared_data, screens=screens)
        return cls(session_data=session_data)

    def save_to_file(self, filename: str) -> None:
        with open(filename, 'w') as f:
            f.write(self.to_json())

    @classmethod
    def load_from_file(cls, filename: str) -> 'SharedStorage':
        with open(filename, 'r') as f:
            return cls.from_json(f.read())
