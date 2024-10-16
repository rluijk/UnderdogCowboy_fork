


from textual import on
from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.widgets import Footer, Label, ListItem, ListView
from textual.widgets import Static, Input, Button, Label, Checkbox
import asyncio


# Events
from events.category_events import CategoryLoaded

# UI
from ui_components.category_scale_widget_ui import CategoryScaleWidget

from ui_components.session_dependent import SessionDependentUI

# LLM Related
import asyncio
from concurrent.futures import ThreadPoolExecutor
from agent_llm_handler import send_agent_data_to_llm 


class LLMCallManager():
    """ 
        Here we want to working with the agent_llm_handler's: send_agent_data_to_llm method.
        
        In the class here:
         - we want to use ThreadPoolExecutor as we do in the AnalyzeUI, and call in this case send_agent_data_to_llm (the AnalyzeUI is
         using: from agent_llm_handler import run_analysis, wich is fine for there, but it is actuallly just a simplified wrapper
         around send_agent_data_to_llm.)
         - In this class we can define methods that prepare pre/post prompt parts if needed for the call to the LLM 
         - We also might need a slightly different llm calling function in the agent_llm_hander, because we also communicate
        
         
        - like we also do in AnalyzeUI, we want to that in CategoryEditorUI (see below), is store result with 
        the session manager. So we separate the session/data storoge we do locally from the LLM calls, but
        store the results from the LLM that way.

    """

    # reponses returned are managed via the injected session_manager in the
    # CategoryEditorUI's init method. (below) 

    pass

class CategoryEditorUI(SessionDependentUI):

    def __init__(self, session_manager):
        super().__init__()
        self.session_manager = session_manager  # Store session manager for persistence
        self.selected_category = self.session_manager.get_data('selected_category', "Default Category")
        self.styles.overflow_y = "auto"  # Enable vertical scrolling
        self.styles.height = "500"       # Set a fixed height
        self.llm_call_manager = LLMCallManager()

    def compose(self) -> ComposeResult:
        yield CategoryScaleWidget(self.llm_call_manager)

