import os 
import json

from typing import Optional, Dict, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from .dialog_manager import DialogManager


class Agent:
    """
    Represents an agent with associated content loaded from a JSON file.

    This class encapsulates the properties and behavior of an agent, including
    its identifier, filename, package, and content. It can load agent data
    from a JSON file and handle potential errors during the loading process.

    Attributes:
        id (str): The identifier of the agent, derived from the filename.
        filename (str): The name of the JSON file containing the agent data.
        package (str): The package or directory where the agent file is located.
        is_user_defined (bool): Indicates whether the agent is user-defined.
        content (dict): The loaded content of the agent file.
    """

    dialog_manager: Optional['DialogManager']

    def __init__(self, filename: str, package: str, is_user_defined: bool = False) -> None:
      
        self.id: str = os.path.splitext(filename)[0]
        self.name: str = self.id
        self.filename: str = filename
        self.package: str = package
        self.is_user_defined: bool = is_user_defined
        self.content: Optional[Dict[str, Any]] = self._load_content()
        self.dialog_manager: Optional['DialogManager'] = None

    def __rshift__(self, user_input: str) -> Any:
        """
        Overloads the >> operator to send a message to the agent.

        Args:
            user_input (str): The user's message to send to the agent.

        Returns:
            Any: The agent's response.
        """
        return self.message(user_input)


    def _load_content(self) -> Optional[Dict[str, Any]]:
        try:
            file_path = os.path.join(self.package, self.filename)
            with open(file_path, 'r') as file:
                content = file.read()
            return json.loads(content)
        except FileNotFoundError:
            print(f"Agent file {self.filename} not found.")
            return None 
        except Exception as e:
            print(f"Error loading agent file: {str(e)}")
            return None
    
    def message(self, user_input: str) -> Any:
        if self.dialog_manager is None:
            raise ValueError("Agent is not registered with a dialog manager")

        response = self.dialog_manager.message(self, user_input)
        return response    


    def register_with_dialog_manager(self, dialog_manager: 'DialogManager') -> None:                  
        if self.dialog_manager != dialog_manager:
            self.dialog_manager = dialog_manager
            self.dialog_manager.prepare_agent(self)    