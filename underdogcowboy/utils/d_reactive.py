import logging
from typing import Any
import inspect
import os

from textual.reactive import Reactive
from textual.widgets import Static

""" the exception is not used for now, just logging a detection """
class WatcherChainError(Exception):
    def __init__(self, current_watcher: str, property_name: str):
        message = f"Watcher chain detected: '{current_watcher}' attempting to set '{property_name}'"
        super().__init__(message)

class DebugStatic(Static):
    """Static widget with debugging logic for reactive properties."""

    def __setattr__(self, name: str, value: Any) -> None:
        if hasattr(type(self), name):
            attr = getattr(type(self), name)
            if isinstance(attr, Reactive):
                stack = inspect.stack()
                project_root = os.path.dirname(os.path.abspath(__file__))
                current_watcher = None
                for frame_info in stack[1:]:
                    function_name = frame_info.function
                    frame = frame_info.frame
                    # Check if function is a watcher in your code
                    if function_name.startswith('watch_'):
                        module = inspect.getmodule(frame)
                        if module:
                            module_file = getattr(module, '__file__', '')
                            # Exclude third-party modules
                            if module_file and module_file.startswith(project_root):
                                frame_self = frame.f_locals.get('self', None)
                                if frame_self is self:
                                    current_watcher = function_name
                                    break
                if current_watcher:
                    logging.warning(
                        f"Watcher chain detected: '{current_watcher}' attempting to set '{name}'"
                    )
                    # Optionally
                    # raise WatcherChainError(current_watcher, name).with_traceback(None)



        super().__setattr__(name, value)
