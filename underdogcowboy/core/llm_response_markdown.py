
import logging
import textwrap
import re
from typing import Optional

import mdformat
from rich.console import Console
from rich.markdown import Markdown

# Configure logging before any other imports
logging.basicConfig(level=logging.WARNING)

# Suppress logs from markdown_it and rich libraries
loggers_to_suppress = [
    'markdown_it',
    'rich',
    # Add other logger names here if needed
]

for logger_name in loggers_to_suppress:
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.WARNING)
    logger.propagate = False

class LLMResponseRenderer:
    """
    A class to clean, format, and render LLM responses as Markdown in the console using Rich.
    """

    def __init__(
        self,
        console: Optional[Console] = None,
        mdformat_config_path: Optional[str] = None,
        log_level: int = logging.WARNING,
    ):
        """
        Initializes the LLMResponseRenderer.

        :param console: An instance of Rich Console. If None, a new Console is created.
        :param mdformat_config_path: Path to the mdformat configuration file. If None, default settings are used.
        :param log_level: Logging level. Default is logging.WARNING.
        """
        # Configure logging
        self.logger = logging.getLogger(__name__)
        self.set_log_level(log_level)
        self.logger.propagate = False

        # Initialize Rich Console
        self.console = console if console else Console()

        # Store mdformat configuration path
        self.mdformat_config_path = mdformat_config_path

    def set_log_level(self, log_level: int):
        """
        Set the log level for the renderer.

        :param log_level: The desired log level (e.g., logging.DEBUG, logging.INFO, logging.WARNING)
        """
        self.logger.setLevel(log_level)

    def clean_response(self, response: str) -> str:
        """
        Cleans the model response to ensure proper Markdown syntax.

        :param response: The raw model response string.
        :return: Cleaned response string.
        """
        try:
            self.logger.info("Starting to clean the model response.")

            # Remove leading/trailing whitespace
            response = response.strip()
            self.logger.debug("Stripped leading and trailing whitespace.")

            # Remove unintended indentation
            response = textwrap.dedent(response)
            self.logger.debug("Removed unintended indentation.")

            # Correct ordered list syntax: ensure numbers are followed by a period
            response = re.sub(r'^(\d+)\s', r'\1. ', response, flags=re.MULTILINE)
            self.logger.debug("Corrected ordered list syntax.")

            # Ensure there are blank lines before and after lists
            response = re.sub(r'\n(\d+\.)', r'\n\n\1', response)
            response = re.sub(r'(\d+\.\s.+?)(?=\n\d+\.\s|\n{2,})', r'\1\n', response)
            self.logger.debug("Ensured blank lines around lists.")

            # Correct unordered lists: ensure dashes or asterisks are followed by a space
            response = re.sub(r'^-\s*', r'* ', response, flags=re.MULTILINE)
            response = re.sub(r'^\*\s*', r'* ', response, flags=re.MULTILINE)
            self.logger.debug("Corrected unordered list syntax.")

            # Handle code blocks if present (ensure proper fencing)
            response = self._correct_code_blocks(response)

            # Optionally, escape special characters if necessary
            # Uncomment the following line if you need to escape special characters
            # response = self._escape_special_characters(response)

            self.logger.info("Finished cleaning the model response.")
            return response

        except Exception as e:
            self.logger.error(f"Error during cleaning: {e}")
            return response  # Fallback to original response

    def _correct_code_blocks(self, response: str) -> str:
        """
        Ensures that code blocks are properly fenced with triple backticks.

        :param response: The response string.
        :return: Response string with corrected code blocks.
        """
        # Add a newline before and after existing code fences if missing
        response = re.sub(r'```', r'\n```\n', response)
        self.logger.debug("Corrected code blocks.")
        return response

    def _escape_special_characters(self, response: str) -> str:
        """
        Escapes Markdown special characters to prevent unintended formatting.

        :param response: The response string.
        :return: Response string with escaped special characters.
        """
        special_chars = ['\\', '`', '*', '_', '{', '}', '[', ']', '(', ')', '#', '+', '-', '.', '!']
        for char in special_chars:
            response = response.replace(char, f'\\{char}')
        self.logger.debug("Escaped special characters.")
        return response

    def format_markdown(self, cleaned_response: str) -> str:
        """
        Formats the cleaned Markdown using mdformat.

        :param cleaned_response: The cleaned Markdown string.
        :return: Formatted Markdown string.
        """
        try:
            self.logger.info("Starting Markdown formatting with mdformat.")

            if self.mdformat_config_path:
                # Use a configuration file if provided
                formatted = mdformat.text(cleaned_response, config=self.mdformat_config_path)
                self.logger.debug("Formatted Markdown using mdformat with configuration file.")
            else:
                # Use default mdformat settings
                formatted = mdformat.text(cleaned_response)
                self.logger.debug("Formatted Markdown using mdformat with default settings.")

            self.logger.info("Finished Markdown formatting.")
            return formatted

        except Exception as e:
            self.logger.error(f"Error during Markdown formatting: {e}")
            return cleaned_response  # Fallback to cleaned response

    def render_markdown(self, formatted_response: str, title: Optional[str] = None):
        """
        Renders the formatted Markdown in the console using Rich.

        :param formatted_response: The formatted Markdown string.
        :param title: Optional title for the response.
        """
        try:
            self.logger.info("Starting to render Markdown in console.")

            # Create Markdown-formatted text with an optional heading
            if title:
                markdown_text = f"### 💬 **{title}**\n\n{formatted_response}"
            else:
                markdown_text = f"### 💬 **LLM Response**\n\n{formatted_response}"

            # Define separators
            separator = "-" * 30

            # Print with separators
            self.console.print(f"\n{separator}\n")
            self.console.print(Markdown(markdown_text))
            self.console.print(f"{separator}\n")
            self.logger.info("Finished rendering Markdown in console.")

        except Exception as e:
            self.logger.error(f"Error during rendering: {e}")
            self.console.print(f"An error occurred while rendering the response: {e}", style="bold red")

    def process_and_render(
        self, model_response: str, title: Optional[str] = None
    ):
        """
        Cleans, formats, and renders the model response.

        :param model_response: The raw model response string.
        :param title: Optional title for the response.
        """
        self.logger.info("Processing and rendering the model response.")
        cleaned = self.clean_response(model_response)
        formatted = self.format_markdown(cleaned)
        self.render_markdown(formatted, title)
        self.logger.info("Completed processing and rendering.")
