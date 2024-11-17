import os 
import json

from typing import ( TYPE_CHECKING, 
                     Union,Optional,
                     Dict, Any )

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
        self.response = None

    def __rshift__(self, other: Union[str, 'Agent']) -> Any:
        """
        Overloads the >> operator to send a message to the agent.

        Args:
            other (Union[str, Agent]): The user's message or another agent.

        Returns:
            Any: The agent's response.
        """
        if isinstance(other, Agent):
            # If 'other' is an Agent, use its last response
            message = other.get_last_response()
        else:
            # If 'other' is a string, use it directly
            message = other

        return self.message(message)

    def __or__(self, other_agent):
        """
        Overloads the | operator to perform operations between agents.

        Args:
            other_agent: Another agent to interact with.

        Returns:
            Any: The result of the interaction between agents.
        """
        if hasattr(other_agent, 'compress') and callable(other_agent.compress):
            # If other_agent has a compress method, use it
            return other_agent.compress(self.content)
        elif hasattr(self, 'process') and callable(self.process):
            # If self has a process method, use it with other_agent
            return self.process(other_agent)
        else:
            raise TypeError(f"Unsupported operation between {self.__class__.__name__} and {other_agent.__class__.__name__}")

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

        self.response = self.dialog_manager.message(self, user_input)
        return self.response    

    def get_last_response(self) -> Optional[str]:
        """
        Returns the last response of the agent.
        If there's no response yet, returns None.
        """
        return self.response.text if self.response else None

    def register_with_dialog_manager(self, dialog_manager: 'DialogManager') -> None:                  
        if self.dialog_manager != dialog_manager:
            self.dialog_manager = dialog_manager
            self.dialog_manager.prepare_agent(self)    

    def assess(self,msg: str) -> bool:
        return True        
    
    def receive_update(self, update_data: dict):
        """
        Handle updates sent from the CLI.

        Args:
            update_data (dict): The data being sent as an update.
        """
        # For demonstration, we'll simply print the update.
        # Replace this with actual logic to handle the update as needed.
        print("Agent received update (in):")
        print(json.dumps(update_data, indent=2))