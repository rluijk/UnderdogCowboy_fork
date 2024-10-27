import logging

from textual.app import ComposeResult

# UI
from ui_components.category_scale_widget_ui_candidate import CategoryScaleWidget
from ui_components.session_dependent import SessionDependentUI

# LLM Related
from llm_call_manager import LLMCallManager


class CategoryEditorUI(SessionDependentUI):


    def __init__(self, session_manager, screen_name, agent_name_plain):
        super().__init__(session_manager, screen_name, agent_name_plain)
        self.session_manager = session_manager
        self.selected_category = self.session_manager.get_data('selected_category', "Default Category")
        logging.info(f"selected at init of CategoryEditorUI: {self.selected_category}")
        self.styles.overflow_y = "auto"  # Enable vertical scrolling
        self.styles.height = "500"       # Set a fixed height
        self.agent_name_plain = agent_name_plain

    def compose(self) -> ComposeResult:
        yield CategoryScaleWidget(self.agent_name_plain)

