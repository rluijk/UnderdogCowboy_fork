import logging

import asyncio
from concurrent.futures import ThreadPoolExecutor

from textual.widgets import Static, Button, LoadingIndicator
from textual.app import ComposeResult

from events.analysis_events import AnalysisComplete, AnalysisError  
from agent_llm_handler import run_analysis
from session_manager import SessionManager

from ui_components.session_dependent import SessionDependentUI

#  Clear existing handlers and set up logging to a file
for handler in logging.root.handlers[:]:
    logging.root.removeHandler(handler)


class AnalyzeUI(SessionDependentUI):
    """A UI for displaying and running analysis on an agent definition"""
    

    def compose(self) -> ComposeResult:
        yield Static("Analysis Result:", id="result-label", classes="hidden")
        yield Static(id="analysis-result", classes="hidden")
        yield Button("Start Analysis", id="start-analysis-button", classes="hidden")
        yield Button("Re-run Analysis", id="rerun-analysis-button", classes="hidden")
        yield LoadingIndicator(id="loading-indicator", classes="hidden")

    def on_mount(self) -> None:
        self.check_existing_analysis()

    def check_existing_analysis(self) -> None:
        existing_analysis = self.session_manager.get_data("last_analysis", screen_name=self.screen_name)
        if existing_analysis:
            self.show_result(existing_analysis)
            self.query_one("#rerun-analysis-button").remove_class("hidden")
        else:
            self.query_one("#start-analysis-button").remove_class("hidden")


    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id in ["start-analysis-button", "rerun-analysis-button"]:
            self.run_analysis()

    def run_analysis(self) -> None:
        self.query_one("#start-analysis-button").add_class("hidden")
        self.query_one("#rerun-analysis-button").add_class("hidden")
        self.query_one("#analysis-result").add_class("hidden")
        self.query_one("#loading-indicator").remove_class("hidden")

        # Create a task to run the analysis
        asyncio.create_task(self.perform_analysis())

    async def perform_analysis(self) -> None:
        try:
            logging.info("Analysis started")
            
            llm_config = self.app.get_current_llm_config()
            if not llm_config:
                raise ValueError("No LLM configuration available.")

            current_agent = self.agent_name_plain
            if not current_agent:
                raise ValueError("No agent currently loaded. Please load an agent first.")

            # Run the analysis in a separate thread pool
            with ThreadPoolExecutor(max_workers=1) as executor:
                result = await asyncio.get_event_loop().run_in_executor(
                    executor, run_analysis, llm_config, current_agent
                )

            if result.startswith("Error:"):
                raise ValueError(result)

            logging.info("Analysis completed")
            self.post_message(AnalysisComplete(result))
        except Exception as e:
            logging.error(f"Analysis error: {str(e)}")
            self.post_message(AnalysisError(str(e)))

    def on_analysis_complete(self, message: AnalysisComplete) -> None:
        self.update_and_show_result(message.result)
        self.query_one("#loading-indicator").add_class("hidden")

    def on_analysis_error(self, message: AnalysisError) -> None:
        self.show_error(message.error)
        self.query_one("#loading-indicator").add_class("hidden")

    def update_and_show_result(self, result: str) -> None:
        self.session_manager.update_data("last_analysis", result)
        self.show_result(result)

    def show_result(self, result: str) -> None:
        self.query_one("#loading-indicator").add_class("hidden")
        self.query_one("#result-label").remove_class("hidden")
        result_widget = self.query_one("#analysis-result")
        result_widget.update(result)
        result_widget.remove_class("hidden")
        self.query_one("#rerun-analysis-button").remove_class("hidden")

    def show_error(self, error_message: str) -> None:
        self.query_one("#loading-indicator").add_class("hidden")
        self.query_one("#start-analysis-button").remove_class("hidden")
        self.app.notify(f"Error: {error_message}", severity="error")

