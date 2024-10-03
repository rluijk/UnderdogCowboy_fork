from dataclasses import dataclass, field
from typing import Any, Dict, List

@dataclass
class SharedData:
    version: str = "1.0.0"
    data: Dict[str, Any] = field(default_factory=dict)
    command_history: List[Dict[str, Any]] = field(default_factory=list)

@dataclass
class ScreenData:
    data: Dict[str, Any] = field(default_factory=dict)
    command_history: List[Dict[str, Any]] = field(default_factory=list)

@dataclass
class SessionData:
    shared_data: SharedData = field(default_factory=SharedData)
    screens: Dict[str, ScreenData] = field(default_factory=dict)
