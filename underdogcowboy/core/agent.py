import json
import importlib.resources as pkg_resources


class Agent:
    def __init__(self, filename):
        self.id = filename.split('.')[0]
        self.filename = filename
        self.content = self._load_content()
      
    def _load_content(self):
        try:
            # Assuming 'agents' is a package in your project structure
            content = pkg_resources.read_text('underdogcowboy.agents', self.filename)
            return json.loads(content)
        except FileNotFoundError:
            print(f"Agent file {self.filename} not found.")
            return None
        except Exception as e:
            print(f"Error loading agent file: {str(e)}")
            return None

language_agent = Agent("new language.json")