from concurrent.futures import ThreadPoolExecutor
import asyncio
import logging
import os
import json
from textual.app import ComposeResult
from textual.widgets import Static, Button, Label, LoadingIndicator
from events.feedback_events import FeedbackInputComplete, FeedbackInputError
from agent_llm_handler import send_agent_data_to_llm  

from session_manager import SessionManager
from ui_components.session_dependent import SessionDependentUI

class FeedbackInputUI(SessionDependentUI):
    """A UI for getting feedback from the underlying agent on how it understands the structure of the input it receives."""
    
    def compose(self) -> ComposeResult:
        yield Label("Feedback on Input Structure:", id="feedback-input-label", classes="hidden")
        yield Static(id="feedback-input-result", classes="feedback-result hidden")
        yield Button("Start Feedback", id="start-feedback-input-button", classes="hidden")
        yield Button("Re-run Feedback", id="rerun-feedback-input-button", classes="hidden")
        yield LoadingIndicator(id="loading-feedback-input", classes="hidden")

    def on_mount(self) -> None:
        self.check_existing_feedback()
    
    def check_existing_feedback(self) -> None:
        existing_feedback = self.session_manager.get_data("last_feedback_input")
        if existing_feedback:
            self.show_feedback(existing_feedback)
            self.query_one("#rerun-feedback-input-button").remove_class("hidden")
        else:
            self.query_one("#start-feedback-input-button").remove_class("hidden")
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id in ["start-feedback-input-button", "rerun-feedback-input-button"]:
            self.run_feedback()
    
    def run_feedback(self) -> None:
        self.query_one("#start-feedback-input-button").add_class("hidden")
        self.query_one("#rerun-feedback-input-button").add_class("hidden")
        self.query_one("#feedback-input-result").add_class("hidden")
        self.query_one("#loading-feedback-input").remove_class("hidden")

        # Use asyncio to manage the feedback task asynchronously
        asyncio.create_task(self.perform_feedback())

    async def perform_feedback(self) -> None:
        try:
            llm_config = self.app.get_current_llm_config()
            if not llm_config:
                raise ValueError("No LLM configuration available.")
            
            current_agent = self.agent_name_plain
            if not current_agent:
                raise ValueError("No agent currently loaded. Please load an agent first.")
            
            # Use ThreadPoolExecutor to run feedback in the background
            with ThreadPoolExecutor(max_workers=1) as executor:
                # Use send_agent_data_to_llm to request feedback from the LLM via the 'clarity' agent
                pre_prompt = "Provide feedback on how the following agent understands the structure of the input it receives."
                result = await asyncio.get_event_loop().run_in_executor(
                    executor, send_agent_data_to_llm, llm_config, current_agent, 'clarity', pre_prompt
                )

            if result.startswith("Error:"):
                raise ValueError(result)

            self.post_message(FeedbackInputComplete(result))
        except Exception as e:
            logging.error(f"Feedback error: {str(e)}")
            self.post_message(FeedbackInputError(str(e)))

    def on_feedback_input_complete(self, message: FeedbackInputComplete) -> None:
        self.update_and_show_feedback(message.result)
        self.query_one("#loading-feedback-input").add_class("hidden")

    def on_feedback_input_error(self, message: FeedbackInputError) -> None:
        self.show_error(message.error)
        self.query_one("#loading-feedback-input").add_class("hidden")

    def update_and_show_feedback(self, result: str) -> None:
        self.app.session_manager.update_data("last_feedback_input", result)
        self.show_feedback(result)

    def show_feedback(self, result: str) -> None:
        self.query_one("#loading-feedback-input").add_class("hidden")
        self.query_one("#feedback-input-label").remove_class("hidden")
        feedback_widget = self.query_one("#feedback-input-result")
        feedback_widget.update(result)
        feedback_widget.remove_class("hidden")
        self.query_one("#rerun-feedback-input-button").remove_class("hidden")

    def show_error(self, error_message: str) -> None:
        self.query_one("#loading-feedback-input").add_class("hidden")
        self.query_one("#start-feedback-input-button").remove_class("hidden")
        self.app.notify(f"Error: {error_message}", severity="error")
