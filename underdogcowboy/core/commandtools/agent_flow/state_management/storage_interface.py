from abc import ABC, abstractmethod
from typing import List
from dataclasses import dataclass

from state_management.shared_data import SessionData

class StorageInterface(ABC):
    @abstractmethod
    def create_session(self, name: str) -> SessionData:
        pass

    @abstractmethod
    def load_session(self, name: str) -> SessionData:
        pass

    @abstractmethod
    def save_session(self, name: str, session_data: SessionData) -> None:
        pass

    @abstractmethod
    def list_sessions(self) -> List[str]:
        pass
