import os
import json
from typing import List
from dataclasses import asdict

from state_management.storage_interface import StorageInterface
from state_management.shared_data import SessionData, ScreenData, SharedData 

class JSONStorageManager(StorageInterface):
    def __init__(self, base_dir: str = ".uccli_sessions"):
        self.base_dir = os.path.expanduser(base_dir)
        self.ensure_base_dir()

    def ensure_base_dir(self):
        os.makedirs(self.base_dir, exist_ok=True)

    def get_session_file_path(self, name: str) -> str:
        return os.path.join(self.base_dir, f"{name}.json")

    def create_session(self, name: str) -> SessionData:
        session_path = self.get_session_file_path(name)
        if os.path.exists(session_path):
            raise ValueError(f"Session '{name}' already exists")
        session_data = SessionData()
        self.save_session(name, session_data)
        return session_data

    def load_session(self, name: str) -> SessionData:
        session_path = self.get_session_file_path(name)
        if not os.path.exists(session_path):
            raise ValueError(f"Session '{name}' does not exist")
        with open(session_path, 'r') as f:
            data = json.load(f)
            return self.deserialize_session_data(data)

    def save_session(self, name: str, session_data: SessionData) -> None:
        session_path = self.get_session_file_path(name)
        data = self.serialize_session_data(session_data)
        with open(session_path, 'w') as f:
            json.dump(data, f, default=str, indent=2)

    def list_sessions(self) -> List[str]:
        return [f.replace('.json', '') for f in os.listdir(self.base_dir) if f.endswith('.json')]

    def serialize_session_data(self, session_data: SessionData) -> dict:
        # Convert dataclasses to dictionaries recursively
        def dataclass_to_dict(obj):
            if isinstance(obj, list):
                return [dataclass_to_dict(item) for item in obj]
            elif isinstance(obj, dict):
                return {k: dataclass_to_dict(v) for k, v in obj.items()}
            elif hasattr(obj, '__dataclass_fields__'):
                return {k: dataclass_to_dict(v) for k, v in asdict(obj).items()}
            else:
                return obj
        return dataclass_to_dict(session_data)

    def deserialize_session_data(self, data: dict) -> SessionData:
        # Reconstruct SessionData from dictionary
        shared_data = SharedData(
            version=data.get("shared_data", {}).get("version", "1.0.0"),
            data=data.get("shared_data", {}).get("data", {}),
            command_history=data.get("shared_data", {}).get("command_history", [])
        )
        screens = {}
        for screen_name, screen_info in data.get("screens", {}).items():
            screens[screen_name] = ScreenData(
                data=screen_info.get("data", {}),
                command_history=screen_info.get("command_history", [])
            )
        return SessionData(shared_data=shared_data, screens=screens)
