import os 
import json

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
    def __init__(self, filename, package, is_user_defined=False):
        self.id = os.path.splitext(filename)[0]
        self.filename = filename
        self.package = package
        self.is_user_defined = is_user_defined
        self.content = self._load_content()
        self.dialog_manager = None
    
    def _load_content(self):
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
    
    def message(self, user_input):
        if self.dialog_manager is None:
            raise ValueError("Agent is not registered with a dialog manager")

        response = self.dialog_manager.message(self, user_input)
        return response    


    def register_with_dialog_manager(self, dialog_manager):
        if self.dialog_manager != dialog_manager:
            self.dialog_manager = dialog_manager
            self.dialog_manager.prepare_agent(self)    