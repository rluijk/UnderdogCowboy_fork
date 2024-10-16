import logging
import asyncio

from textual import on
from textual.widgets import Static, Button, LoadingIndicator, Label
from textual.containers import Horizontal
from textual.app import ComposeResult

from ui_components.session_dependent import SessionDependentUI
from agent_llm_handler import run_analysis
from llm_call_manager import LLMCallManager

from events.llm_events import LLMCallComplete, LLMCallError
from events.copy_paste_events import LLMResultReceived

# experimental
from llm_response_markdown_renderer import LLMResponseRenderer

renderer = LLMResponseRenderer(
    mdformat_config_path=None,  # Provide path if you have a custom config
)

class AnalyzeUI(SessionDependentUI):
    
    """A UI for displaying and running analysis on an agent definition"""

    def __init__(self, session_manager, screen_name, agent_name_plain):
        super().__init__(session_manager, screen_name, agent_name_plain)
        self.session_manager = session_manager
        self.llm_call_manager = LLMCallManager()
        self.llm_call_manager.set_message_post_target(self)
        logging.info(f"post target message set to: {self.llm_call_manager._message_post_target}")

    def compose(self) -> ComposeResult:
        yield Static("Analysis Result:", id="result-label", classes="hidden")
        yield Static(id="analysis-result", classes="hidden")
        with Horizontal(id="analyze-box"):
            yield Label("Let Agent Clarity, run your first analysis on the agent you loaded")
            yield Button("Start Analysis", id="start-analysis-button", classes="action-button")
        yield Button("Re-run Analysis", id="rerun-analysis-button", classes="hidden action-button")
        yield LoadingIndicator(id="loading-indicator", classes="hidden")

    def on_mount(self) -> None:
        self.check_existing_analysis()

    def check_existing_analysis(self) -> None:
        existing_analysis = self.session_manager.get_data("last_analysis", screen_name=self.screen_name)
        analyze_box = self.query_one("#analyze-box")  # Horizontal container for label and start-analysis button
        if existing_analysis:
            self.show_result(existing_analysis)
            self.query_one("#rerun-analysis-button").remove_class("hidden")
            analyze_box.add_class("hidden")  # Hide the horizontal group
        else:
            analyze_box.remove_class("hidden")  # Ensure horizontal group is visible
            self.query_one("#start-analysis-button").remove_class("hidden")  # Ensure the start button is visible

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id in ["start-analysis-button", "rerun-analysis-button"]:
            self.run_analysis()

    def run_analysis(self) -> None:
        analyze_box = self.query_one("#analyze-box")  # Horizontal container
        analyze_box.add_class("hidden")  # Hide the entire horizontal group
        self.query_one("#rerun-analysis-button").add_class("hidden")
        self.query_one("#analysis-result").add_class("hidden")
        self.query_one("#loading-indicator").remove_class("hidden")

        llm_config = self.app.get_current_llm_config()
        if not llm_config:
            self.show_error("No LLM configuration available.")
            return

        current_agent = self.agent_name_plain
        if not current_agent:
            self.show_error("No agent currently loaded. Please load an agent first.")
            return

        logging.info("sending from ui candidate to the LLMCallManager.")

        asyncio.create_task(self.llm_call_manager.submit_analysis_call(
            llm_function=run_analysis,
            llm_config=llm_config,
            agent_name= current_agent,
            input_id="analysis",
            pre_prompt="Analyze this agent definition:",
            post_prompt=None
        ))

        logging.info("did send from ui candidate to the LLMCallManager.")

        
    @on(LLMCallComplete)
    async def on_llm_call_complete(self, event: LLMCallComplete) -> None:
        if event.input_id == "analysis":
            self.post_message(LLMResultReceived(sender=self, result=event.result))
            self.update_and_show_result(event.result)
            self.query_one("#loading-indicator").add_class("hidden")

    @on(LLMCallError)
    async def on_llm_call_error(self, event: LLMCallError) -> None:
        if event.input_id == "analysis":
            self.show_error(event.error)
            self.query_one("#loading-indicator").add_class("hidden")

    def update_and_show_result(self, result: str) -> None:
        logging.info(f"Entering in update error: result var: {result}")
        self.session_manager.update_data("last_analysis", result)
        self.show_result(result)

    def show_result(self, result: str) -> None:
        self.query_one("#loading-indicator").add_class("hidden")
        self.query_one("#result-label").remove_class("hidden")
        result_widget = self.query_one("#analysis-result")
        # get nice markdown back in the TUI
        renderable = renderer.get_renderable(result, title="LLM Response")
        result_widget.update(renderable)
        result_widget.remove_class("hidden")
        self.query_one("#rerun-analysis-button").remove_class("hidden")

    def show_error(self, error_message: str) -> None:
        self.query_one("#loading-indicator").add_class("hidden")
        self.query_one("#start-analysis-button").remove_class("hidden")
        self.app.notify(f"Error: {error_message}", severity="error")
