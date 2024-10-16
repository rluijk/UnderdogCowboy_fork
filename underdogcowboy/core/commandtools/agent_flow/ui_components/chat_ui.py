import logging
import os
from typing import Tuple

from rich.markdown import Markdown

from textual import on
from textual.binding import Binding
  
from textual.widgets import Static, TextArea, Button
from textual.app import ComposeResult
from textual.containers import VerticalScroll
from textual import events


from llm_response_markdown_renderer import LLMResponseRenderer
from llm_call_manager import LLMCallManager

# events
from events.chat_events import TextSubmitted
from events.llm_events import LLMCallComplete, LLMCallError
from events.action_events import ActionSelected

# uc
from underdogcowboy.core.config_manager import LLMConfigManager
from underdogcowboy.core.timeline_editor import Timeline, CommandProcessor, Message
from underdogcowboy.core.model import ModelManager, ConfigurableModel

renderer = LLMResponseRenderer(
    mdformat_config_path=None,  # Provide path if you have a custom config
)

class ChatTextArea(TextArea):
    BINDINGS = [
        Binding("ctrl+s", "submit", "Submit", key_display="Ctrl+s", priority=True),
    ]

    def action_submit(self) -> None:
        """Handle the submit action when Shift+Enter is pressed."""
        message = self.text
        logging.info(f"Submitting message: {message}")
        self.text = ""
        self.post_message(TextSubmitted(message))


class ChatUI(Static):

    def __init__(self, name: str, type: str):
        super().__init__()
        
        self.processor = None
        self.da_name = name
        self.loading_message_id = None  # Track the loading indicator
        self.is_scroll_at_bottom = True  # Track if the scroll is at the bottom
        self.chat_history_text = ""  

        logging.info(f"Init of ChatUI")
        
        if type == "dialog":
            self.load_dialog(self.da_name)
        if type == "agent":
            self.load_agent(self.da_name)

        self.llm_call_manager = LLMCallManager()
        self.llm_call_manager.set_message_post_target(self) 


    def compose(self) -> ComposeResult:
        with VerticalScroll(id="chat-scroll", disabled=False):
            yield Static(id="chat-history")
        yield ChatTextArea("", id="chat-textarea")

    def on_mount(self) -> None:
        self.render_chat()

    def load_agent(self, agent_name):
        # Agent specific
        agents_dir = os.path.expanduser("~/.underdogcowboy/agents")
        agent_file = f"{agent_name}.json"

        self._load_processor(agent_file, agents_dir)

    def load_dialog(self, dialog_name):
        # Dialog specific
        dialog_name = f"{dialog_name}.json"
        config_manager: LLMConfigManager = LLMConfigManager()
        dialog_path: str = config_manager.get_general_config().get('dialog_save_path', '')

        self._load_processor(dialog_name, dialog_path)

    def _get_model_and_timeline(self) -> Tuple[ConfigurableModel, Timeline]:
        self.model_id = self.app.get_current_llm_config()["model_id"]

        # TODO: Hard Coded default provider.
        model = ModelManager.initialize_model_with_id("anthropic", self.model_id)
        timeline = Timeline()
        return model, timeline

    def _load_processor(self, file_name: str, path: str) -> None:
        """General method to load a timeline and initialize the command processor."""
        try:
            self.model, self.timeline = self._get_model_and_timeline()
            self.timeline.load(file_name, path=path)
            self.processor = CommandProcessor(self.timeline, self.model)
            logging.info(f"Loaded command processor")
        
        except FileNotFoundError:
            logging.error(f"File {file_name} not found in {path}.")
        except Exception as e:
            logging.error(f"Failed to load processor: {str(e)}")

    def format_messages_to_markdown(self, messages: list) -> str:
        """Unpacks an array of Message objects and returns a markdown-formatted string."""
        markdown_output = ""

        for message in messages:
            markdown_output += f"#### {message.role.capitalize()}:\n{message.text}\n\n"

        return markdown_output


    def render_chat(self):
        """Render chat history in the UI when available."""
        # Update the chat history from the processor's history
        self.chat_history_text = self.format_messages_to_markdown(self.processor.timeline.history)
        chat_widget = self.query_one("#chat-history")
        chat_widget.update(Markdown(self.chat_history_text))

        # Scroll to the bottom of the chat
        chat_scroll = self.query_one("#chat-scroll")
        self.scroll_to_end(chat_scroll)


    def scroll_to_end(self, scrollable: VerticalScroll):
        """Scroll to the bottom of the scrollable widget immediately."""
        scrollable.scroll_end(animate=False, force=True)

    @on(TextSubmitted)
    async def handle_text_submission(self, event: TextSubmitted):
        """Handle the submission of the text."""
        # Append the user message to the chat history
        self.chat_history_text += f"\n#### User:\n{event.text}"
        chat_widget = self.query_one("#chat-history", Static)
        chat_widget.update(Markdown(self.chat_history_text))

        # Scroll to the bottom
        scroll_widget = self.query_one("#chat-scroll", VerticalScroll)
        scroll_widget.scroll_end(animate=False, force=True)

        # Append a loading indicator to the chat history
        self.chat_history_text += f"\n#### Assistant:\n..."
        chat_widget.update(Markdown(self.chat_history_text))
        scroll_widget.scroll_end(animate=False, force=True)

        # Store the length of the loading indicator for later removal
        self.loading_indicator_length = len("\n#### Assistant:\n...")

        # Prepare arguments for the LLM call
        llm_config = self.app.get_current_llm_config()
        agent_name = self.da_name
        agent_type = "agent"  # or "dialog" depending on your use case
        input_id = self.loading_indicator_length  # Unique identifier for the input
        pre_prompt = event.text  # The user's message
        post_prompt = None  # Provide if needed

        # Submit the LLM call asynchronously using LLMCallManager
        await self.llm_call_manager.submit_llm_call(
            self.llm_processing_function,
            llm_config,
            agent_name,
            agent_type,
            input_id,      # Correctly include input_id here
            pre_prompt,
            post_prompt
        )

    def llm_processing_function(self, llm_config, agent_name, agent_type, pre_prompt, post_prompt):
        """Function that processes the LLM call."""
        try:
            # Use pre_prompt as the message text
            message_text = pre_prompt
            response = self.processor._process_message(message_text)
            return response
        except Exception as e:
            logging.error(f"Error processing LLM call: {e}")
            raise

    @on(LLMCallComplete)
    def handle_llm_call_complete(self, event: LLMCallComplete):
        """Handle successful LLM call completion."""
        # Remove the loading indicator from the chat history
        self.chat_history_text = self.chat_history_text[:-self.loading_indicator_length]

        # Append the assistant's response
        self.chat_history_text += f"\n#### Assistant:\n{event.result[0]}"

        # Update the widget with the new content
        chat_widget = self.query_one("#chat-history", Static)
        chat_widget.update(Markdown(self.chat_history_text))

        # Scroll to the bottom
        scroll_widget = self.query_one("#chat-scroll", VerticalScroll)
        scroll_widget.scroll_end(animate=False, force=True)

    @on(LLMCallError)
    def handle_llm_call_error(self, event: LLMCallError):
        """Handle errors from the LLM call."""
        # Remove the loading indicator from the chat history
        self.chat_history_text = self.chat_history_text[:-self.loading_indicator_length]

        # Append the error message
        error_message = f"An error occurred: {event.error}"
        self.chat_history_text += f"\n#### Assistant:\n{error_message}"

        # Update the widget with the new content
        chat_widget = self.query_one("#chat-history", Static)
        chat_widget.update(Markdown(self.chat_history_text))

        # Scroll to the bottom
        scroll_widget = self.query_one("#chat-scroll", VerticalScroll)
        scroll_widget.scroll_end(animate=False, force=True)

    def append_to_chat(self, text: str, role: str, move_to_bottom: bool = False) -> int:
        """Append a new message to the chat."""
        # Update the chat history text
        self.chat_history_text += f"\n#### {role}:\n{text}"

        # Update the widget with the new Markdown content
        chat_widget = self.query_one("#chat-history", Static)
        chat_widget.update(Markdown(self.chat_history_text))

        if move_to_bottom:
            scroll_widget = self.query_one("#chat-scroll", VerticalScroll)
            scroll_widget.scroll_end(animate=False, force=True)

        return len(self.chat_history_text)  # Return the length of the chat history as a simple ID

        
    def save_dialog(self):
        logging.info("Executing save_dialog logic in ChatUI.")
        # Use the da_name as filename
        filename = f"{self.da_name}.json"
        
        # Optional: Provide a name and description or leave as None
        name = self.da_name.plain  
        description = "Saved Dialog from ChatUI" 

        # Call the new method to save without prompt
        self.processor.save_timeline_without_prompt(filename, name=name, description=description)

        # Notify the user (if you have a method for this)
        self.app.notify(f"Dialog '{self.da_name}' saved successfully.")

    def save_agent(self):
        logging.info("Executing save_agent logic in ChatUI.")
        # Use the da_name as filename
        filename = f"{self.da_name}.json"
        
        # Optional: Provide a name and description or leave as None
        name = self.da_name  
        description = "Saved Agent from ChatUI" 

        # Call the new method to save without prompt
        self.processor.save_agent_without_prompt(filename, name=name, description=description)

        # Notify the user (if you have a method for this)
        self.app.notify(f"Agent '{self.da_name}' saved successfully.")
 