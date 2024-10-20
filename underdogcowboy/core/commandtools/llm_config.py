import cmd
from underdogcowboy.core.config_manager import LLMConfigManager

class LLMConfigProcessor(cmd.Cmd):
    intro = "Welcome to the LLM Configuration Manager. Type 'help' or '?' to list commands."
    prompt = "(llm_config) "

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
        """Select a model to configure. Usage: select_model <number or name>"""
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
        self.prompt = f"(llm_config:{self.current_model}) "
        self.do_show_config("")

    def __back__do_show_config(self, arg):
        """Show configuration for the currently selected model."""
        if not self.current_model:
            print("No model selected. Please use 'select_model' first.")
            return
        config = self.config_manager.get_credentials(self.current_model)
        print(f"Configuration for {self.current_model}:")
        for i, (key, value) in enumerate(config.items(), 1):
            if key == 'api_key':
                print(f"  {i}. {key}: ****")
            else:
                print(f"  {i}. {key}: {value}")

    def do_show_config(self, arg):
        if not self.current_model:
            print("No model selected. Please use 'select_model' first.")
            return
        provider, model_id = self.current_model.split(':', 1)
        config = self.config_manager.get_credentials(self.current_model)
        print(f"Configuration for {self.current_model}:")
        for i, (key, value) in enumerate(config.items(), 1):
            if key == 'api_key':
                print(f"  {i}. {key}: ****")
            else:
                print(f"  {i}. {key}: {value}")

    def do_update_property(self, arg):
        """Update a specific property for the currently selected model."""
        if not self.current_model:
            print("No model selected. Please use 'select_model' first.")
            return
        
        print(f"Updating properties for model: {self.current_model}")
        
        provider, model_id = self.current_model.split(':', 1)
        config = self.config_manager.get_credentials(self.current_model)
        properties = list(config.keys())
        
        print("Select a property to update:")
        for i, prop in enumerate(properties, 1):
            print(f"  {i}. {prop}")
        
        while True:
            try:
                choice = int(input("Enter the number of the property to update: "))
                if 1 <= choice <= len(properties):
                    property_to_update = properties[choice - 1]
                    break
                else:
                    print("Invalid choice. Please try again.")
            except ValueError:
                print("Please enter a valid number.")
        
        new_value = input(f"Enter new value for {property_to_update}: ")
        try:
            self.config_manager.update_model_property(self.current_model, property_to_update, new_value)
            print(f"Updated {property_to_update} for {self.current_model}.")
        except ValueError as e:
            print(f"Error: {e}")

    def do_exit(self, arg):
        """Exit the LLM Configuration Manager."""
        print("Exiting LLM Configuration Manager. Goodbye!")
        return True

    def do_help(self, arg):
        """List available commands with their descriptions."""
        print("Available commands:")
        for method in dir(self):
            if method.startswith('do_'):
                command = method[3:]
                doc = getattr(self, method).__doc__
                print(f"  {command}: {doc}")

    def default(self, line):
        """Handle unknown commands, including direct model selection by number."""
        if line.isdigit():
            self.do_select_model(line)
        else:
            print(f"*** Unknown syntax: {line}")

def main():
    LLMConfigProcessor().cmdloop()

if __name__ == "__main__":
    main()