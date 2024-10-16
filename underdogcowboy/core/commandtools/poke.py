import cmd
import logging
from typing import List, Optional
from underdogcowboy.core.config_manager import LLMConfigManager
from underdogcowboy import AgentDialogManager, test_agent

from prompt_toolkit import prompt, PromptSession
from prompt_toolkit.completion import WordCompleter, Completer, Completion
from prompt_toolkit.document import Document
from prompt_toolkit.shortcuts import CompleteStyle

# Constants
STATIC_PROMPT = "small message back please, we testing if we can reach you"
INTRO_MESSAGE = "Welcome to the LLM Poke Tool. Type 'help' or '?' to list commands."
DEFAULT_PROMPT = "(llm_poke) "

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class CommandCompleter(Completer):
    def __init__(self, llm_poke_processor):
        self.llm_poke_processor = llm_poke_processor
        self.commands = [cmd[3:] for cmd in dir(llm_poke_processor) if cmd.startswith('do_')]

    def get_completions(self, document, complete_event):
        word_before_cursor = document.get_word_before_cursor(WORD=True)
        line = document.text

        if ' ' not in line:
            # Complete commands
            for command in self.commands:
                if command.startswith(word_before_cursor):
                    yield Completion(command, start_position=-len(word_before_cursor))
        else:
            # Command-specific completions
            command = line.split()[0]
            if command == 'select_model':
                for model in self.llm_poke_processor.available_models:
                    if model.startswith(word_before_cursor):
                        yield Completion(model, start_position=-len(word_before_cursor))

class LLMPokeProcessor(cmd.Cmd):
    """
    A command-line interface for interacting with various LLM models.
    """

    intro = INTRO_MESSAGE
    prompt = DEFAULT_PROMPT

    def __init__(self):
        """Initialize the LLMPokeProcessor."""
        super().__init__()
        self.config_manager = LLMConfigManager()
        self.current_model: Optional[str] = None
        self.available_models: List[str] = self.config_manager.get_available_models()

        # Create a CommandCompleter with all available commands
        self.command_completer = CommandCompleter(self)

        # Create a PromptSession with the command completer
        self.session = PromptSession(completer=self.command_completer, complete_style=CompleteStyle.MULTI_COLUMN)

    def do_list_models(self, arg: str) -> None:
        """
        List all available LLM models.

        Args:
            arg (str): Unused, but required by cmd.Cmd.

        Returns:
            None
        """
        logger.info("Available models:")
        for i, model in enumerate(self.available_models, 1):
            logger.info(f"  {i}. {model}")
        logger.info("\nTo select a model, type the number or use 'select_model <number>' or 'select_model <n>'")

    def do_select_model(self, arg: str) -> None:
        """
        Select a model to poke.

        Args:
            arg (str): The model number or name to select.

        Returns:
            None
        """
        if not arg:
            logger.error("Please provide a model number or name. Use 'list_models' to see available options.")
            return

        try:
            if arg.isdigit():
                index = int(arg) - 1
                if 0 <= index < len(self.available_models):
                    self.current_model = self.available_models[index]
                else:
                    raise ValueError(f"Invalid model number. Please choose between 1 and {len(self.available_models)}.")
            else:
                if arg in self.available_models:
                    self.current_model = arg
                else:
                    raise ValueError(f"Model '{arg}' not found. Use 'list_models' to see available options.")

            logger.info(f"Selected model: {self.current_model}")
            self.prompt = f"(llm_poke:{self.current_model}) "
        except ValueError as e:
            logger.error(str(e))

    def do_poke(self, arg: str) -> None:
        """
        Send a static prompt to the selected model.

        Args:
            arg (str): Unused, but required by cmd.Cmd.

        Returns:
            None
        """
        if not self.current_model:
            logger.error("No model selected. Please use 'select_model' first.")
            return

        try:
            provider, model = self.current_model.split(":")
            adm = AgentDialogManager([test_agent], model_name=model)
            logger.info(f"Sending message to: {self.current_model}")
            response = test_agent >> STATIC_PROMPT
            logger.info(f"Response from {self.current_model}: {response}")
        except Exception as e:
            logger.error(f"An error occurred while poking the model: {str(e)}")

    def do_poke_all(self, arg: str) -> None:
        """
        Send a static prompt to all available LLM models.

        Args:
            arg (str): Unused, but required by cmd.Cmd.

        Returns:
            None
        """
        for model in self.available_models:
            try:
                provider, model_name = model.split(":")
                adm = AgentDialogManager([test_agent], model_name=model_name)
                logger.info(f"Sending message to: {model}")
                response = test_agent >> STATIC_PROMPT
                logger.info(f"Response from {model}: {response}\n")
            except Exception as e:
                logger.error(f"An error occurred while poking model {model}: {str(e)}")

    def do_help(self, arg: str) -> None:
        """
        List available commands with their descriptions.

        Args:
            arg (str): Unused, but required by cmd.Cmd.

        Returns:
            None
        """
        logger.info("Available commands:")
        for method in dir(self):
            if method.startswith('do_'):
                command = method[3:]
                doc = getattr(self, method).__doc__
                description = doc.split('\n')[0] if doc else 'No description available.'
                logger.info(f"  {command}: {description}")

    def do_exit(self, arg: str) -> bool:
        """
        Exit the LLM Poke Tool.

        Args:
            arg (str): Unused, but required by cmd.Cmd.

        Returns:
            bool: True to exit the command loop.
        """
        logger.info("Exiting LLM Poke Tool. Goodbye!")
        return True

    def default(self, line: str) -> None:
        """
        Handle unknown commands, including direct model selection by number.

        Args:
            line (str): The input command line.

        Returns:
            None
        """
        if line.isdigit():
            self.do_select_model(line)
        else:
            logger.error(f"Unknown syntax: {line}")

    def cmdloop(self, intro=None):
        """Repeatedly issue a prompt, accept input, parse an initial prefix
        off the received input, and dispatch to action methods, passing them
        the remainder of the line as argument.
        """
        self.preloop()
        if intro is not None:
            self.intro = intro
        if self.intro:
            self.stdout.write(str(self.intro)+"\n")
        stop = None
        while not stop:
            try:
                line = self.session.prompt(self.prompt)
                line = self.precmd(line)
                stop = self.onecmd(line)
                stop = self.postcmd(stop, line)
            except KeyboardInterrupt:
                print("^C")
            except EOFError:
                print("^D")
                break
        self.postloop()

def main() -> None:
    """
    Main function to run the LLM Poke Tool.
    """
    try:
        LLMPokeProcessor().cmdloop()
    except KeyboardInterrupt:
        logger.info("\nReceived keyboard interrupt. Exiting...")
    except Exception as e:
        logger.error(f"An unexpected error occurred: {str(e)}")

if __name__ == "__main__":
    main()
