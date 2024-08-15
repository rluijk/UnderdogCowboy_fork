import cmd
from underdogcowboy.core.config_manager import LLMConfigManager
from underdogcowboy import AgentDialogManager, test_agent

class LLMPokeProcessor(cmd.Cmd):
    intro = "Welcome to the LLM Poke Tool. Type 'help' or '?' to list commands."
    prompt = "(llm_poke) "

    def __init__(self):
        super().__init__()
        self.config_manager = LLMConfigManager()
        self.current_model = None
        self.available_models = self.config_manager.get_available_models()

    def do_list_models(self, arg):
        """List all available LLM models."""
        print("Available models:")
        for i, model in enumerate(self.available_models, 1):
            print(f"  {i}. {model}")
        print("\nTo select a model, type the number or use 'select_model <number>' or 'select_model <name>'")

    def do_select_model(self, arg):
        """Select a model to poke. Usage: select_model <number or name>"""
        if not arg:
            print("Please provide a model number or name. Use 'list_models' to see available options.")
            return

        if arg.isdigit():
            index = int(arg) - 1
            if 0 <= index < len(self.available_models):
                self.current_model = self.available_models[index]
            else:
                print(f"Invalid model number. Please choose between 1 and {len(self.available_models)}.")
                return
        else:
            if arg in self.available_models:
                self.current_model = arg
            else:
                print(f"Model '{arg}' not found. Use 'list_models' to see available options.")
                return

        print(f"Selected model: {self.current_model}")
        self.prompt = f"(llm_poke:{self.current_model}) "

    def do_poke(self, arg):
        """Send a static prompt to the selected model."""
        if not self.current_model:
            print("No model selected. Please use 'select_model' first.")
            return

        static_prompt = "small message back please, we testing if we can reach you"
        adm = AgentDialogManager([test_agent], model_name=self.current_model)
        print(f"Sending message to: {self.current_model}")
        response = test_agent >> static_prompt
        print(f"Response from {self.current_model}: {response}")

    def do_poke_all(self, arg):
        """Send a static prompt to all available LLM models."""
        static_prompt = "small message back please, we testing if we can reach you"

        for model in self.available_models:
            adm = AgentDialogManager([test_agent], model_name=model)
            print(f"Sending message to: {model}")
            response = test_agent >> static_prompt
            print(f"Response from {model}: {response}\n")

    def do_help(self, arg):
        """List available commands with their descriptions."""
        print("Available commands:")
        for method in dir(self):
            if method.startswith('do_'):
                command = method[3:]
                doc = getattr(self, method).__doc__
                print(f"  {command}: {doc}")

    def do_exit(self, arg):
        """Exit the LLM Poke Tool."""
        print("Exiting LLM Poke Tool. Goodbye!")
        return True

    def default(self, line):
        """Handle unknown commands, including direct model selection by number."""
        if line.isdigit():
            self.do_select_model(line)
        else:
            print(f"*** Unknown syntax: {line}")

def main():
    LLMPokeProcessor().cmdloop()

if __name__ == "__main__":
    main()


