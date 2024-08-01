import os
import time
import uuid
from typing import Optional, Any

from underdogcowboy import Agent, LLMConfigManager, DialogManager

class CommitPromoAgent(Agent):
    """
    An agent class for creating LinkedIn promotional posts based on commit messages and code updates.

    This agent generates Western-themed LinkedIn posts highlighting recent improvements or new features
    in the Underdogcowboy (UC) library. It processes commit information, creates a promotional message,
    and saves it as a Markdown file.

    Expected output:
    - A LinkedIn post with a friendly, Western-themed greeting (using 🤠 emoji)
    - Highlights of 2-3 key improvements or new features from recent commits
    - Reinforcement of UC's philosophy on AI agent management
    - Installation instructions and links to GitHub and PyPI
    - Relevant hashtags: #OpenSource #AI #UnderdogCowboy
    - Overall playful and enthusiastic tone with Western-themed metaphors

    The generated post is saved as a Markdown file with a unique identifier in the filename.
    """
    def __init__(self, filename: str, package: str, is_user_defined: bool = False) -> None:
        super().__init__(filename, package, is_user_defined)
        self.response: Optional[str] = None
        self.config_manager: LLMConfigManager = LLMConfigManager()
        self.message_export_path: str = self.config_manager.get_general_config().get('message_export_path', '')

    def save_response(self, msg: str, post_filename: str) -> None:
        if not self.message_export_path:
            print("Error: message_export_path is not set in the configuration.")
            return

        filename: str = os.path.join(self.message_export_path, f"{post_filename}.md")
        markdown_content: str = f"{msg}\n"

        try:
            with open(filename, 'w', encoding='utf-8') as md_file:
                md_file.write(markdown_content)
            print(f"Message exported to Markdown file '{filename}' successfully.")
        except IOError as e:
            print(f"Error writing to file '{filename}': {e}")

    def create_linked_in_post_from_diff(self, file_ref: Any, model_name: str = "anthropic") -> 'CommitPromoAgent':
        self.register_with_dialog_manager(DialogManager([self], model_name))
        self.response = self.message(file_ref)

        # Generate a unique identifier
        unique_id: str = f"{int(time.time())}_{uuid.uuid4().hex[:8]}"

        # Use the unique identifier in the filename
        filename: str = f"linked-in-concept_{unique_id}"

        self.save_response(self.response, filename)
        return self

    def create_json_from_concept_post(self) -> Any:
        prompt: str = f"Can you return the response given in json, but only the actual concept text?"
        return self.message(prompt)