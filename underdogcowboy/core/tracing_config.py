import cmd
from underdogcowboy.core.config_manager import LLMConfigManager

class TracingConfigProcessor(cmd.Cmd):
    intro = "Welcome to the Tracing Configuration Manager. Type 'help' or '?' to list commands."
    prompt = "(tracing_config) "

    def __init__(self):
        super().__init__()
        self.config_manager = LLMConfigManager()

    def do_show(self, arg):
        """Display current tracing configuration."""
        config = self.config_manager.get_tracing_config()
        print("Tracing Configuration:")
        for key, value in config.items():
            if key == 'langsmith_api_key':
                print(f"  {key}: ****")
            else:
                print(f"  {key}: {value}")

    def do_update(self, arg):
        """Update tracing configuration settings."""
        self.config_manager.update_tracing_config()
        print("Tracing configuration updated.")

    def do_toggle_langsmith(self, arg):
        """Toggle LangSmith tracing on or off."""
        config = self.config_manager.get_tracing_config()
        current_status = config.get('use_langsmith', 'no')
        new_status = 'yes' if current_status.lower() == 'no' else 'no'
        self.config_manager.update_model_property('tracing', 'use_langsmith', new_status)
        print(f"LangSmith tracing {'enabled' if new_status == 'yes' else 'disabled'}.")

    def do_help(self, arg):
        """List available commands with their descriptions."""
        print("Available commands:")
        for method in dir(self):
            if method.startswith('do_'):
                command = method[3:]
                doc = getattr(self, method).__doc__
                print(f"  {command}: {doc}")

    def do_exit(self, arg):
        """Exit the Tracing Configuration Manager."""
        print("Exiting Tracing Configuration Manager. Goodbye!")
        return True

def main():
    TracingConfigProcessor().cmdloop()

if __name__ == "__main__":
    main()