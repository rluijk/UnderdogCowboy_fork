import os
import json
from typing import List, Dict
from uccli import GenericCLI, StateMachine, State, command, cancellable_command, input_required_command, StorageManager, AgentCommunicator, DummyAgentCommunicator
from underdogcowboy import UCAgentCommunicator

# Import agentclarity and cliagent from their specific modules
from underdogcowboy  import cliagent

class ModularCLI(GenericCLI):
    def __init__(self):
        # Initialize the state machine
        initial_state = State("initial")
        managing_modules_state = State("managing_modules")
        executing_modules_state = State("executing_modules")

        # Set up transitions
        initial_state.add_transition("manage_modules", managing_modules_state)
        initial_state.add_transition("execute_modules", executing_modules_state)
        
        managing_modules_state.add_transition("execute_modules", executing_modules_state)
        managing_modules_state.add_transition("add_module", managing_modules_state)
        managing_modules_state.add_transition("remove_module", managing_modules_state)
        managing_modules_state.add_transition("list_modules", managing_modules_state)
        managing_modules_state.add_transition("reorder_modules", managing_modules_state)
        
        executing_modules_state.add_transition("manage_modules", managing_modules_state)
        executing_modules_state.add_transition("execute", executing_modules_state)

        state_machine = StateMachine(initial_state)
        state_machine.add_state(managing_modules_state)
        state_machine.add_state(executing_modules_state)

        # Initialize the storage manager and agent communicator
        self.storage_manager = StorageManager(base_dir=os.path.expanduser("~/.modular_cli_sessions"))
        #agent_communicator = DummyAgentCommunicator()
        uc_agent_communicator = UCAgentCommunicator(cliagent)


        super().__init__(state_machine, uc_agent_communicator)

        # Load or create a default session
        default_session_name = "default_session"
        try:
            self.current_storage = self.storage_manager.load_session(default_session_name)
            print(f"Loaded default session: {default_session_name}")
        except ValueError:
            self.current_storage = self.storage_manager.create_session(default_session_name)
            print(f"Created new default session: {default_session_name}")

        # Initialize modules list
        if "modules" not in self.current_storage.data:
            self.current_storage.update_data("modules", [])

        self.current_storage.data.setdefault("modules", [])    

    @command("manage_modules", "Enter the managing modules state")
    def do_manage_modules(self, arg):
        print("Entered managing modules state.")
        return "CONTINUE"

    @command("execute_modules", "Enter the executing modules state")
    def do_execute_modules(self, arg):
        print("Entered executing modules state.")
        return "CONTINUE"

    @command("add_module", "Add a new module to the workflow")
    def do_add_module(self, arg):
        if self.state_machine.current_state.name != "managing_modules":
            print("This command is only available in the managing modules state.")
            return
        if not arg:
            print("Please provide a module name.")
            return
        modules = self.current_storage.get_data("modules")
        modules.append(arg)
        self.current_storage.update_data("modules", modules)
        print(f"Added module: {arg}")

    @command("remove_module", "Remove an existing module from the workflow")
    def do_remove_module(self, arg):
        if self.state_machine.current_state.name != "managing_modules":
            print("This command is only available in the managing modules state.")
            return
        if not arg:
            print("Please provide a module name to remove.")
            return
        modules = self.current_storage.get_data("modules")
        if arg in modules:
            modules.remove(arg)
            self.current_storage.update_data("modules", modules)
            print(f"Removed module: {arg}")
        else:
            print(f"Module not found: {arg}")

    @command("list_modules", "Display all active modules in the workflow")
    def do_list_modules(self, arg):
        if self.state_machine.current_state.name != "managing_modules":
            print("This command is only available in the managing modules state.")
            return
        modules = self.current_storage.get_data("modules")
        if modules:
            print("Active modules:")
            for i, module in enumerate(modules, 1):
                print(f"{i}. {module}")
        else:
            print("No active modules.")

    @command("reorder_modules", "Reorder the sequence of modules in the workflow")
    def do_reorder_modules(self, arg):
        if self.state_machine.current_state.name != "managing_modules":
            print("This command is only available in the managing modules state.")
            return
        new_order = arg.split()
        if not new_order:
            print("Please provide the new order of modules.")
            return
        current_modules = self.current_storage.get_data("modules")
        if set(new_order) != set(current_modules):
            print("The new order must contain all and only the current modules.")
            return
        self.current_storage.update_data("modules", new_order)
        print("Modules reordered successfully.")

    @command("execute", "Run all modules in the workflow sequentially")
    def do_execute(self, arg):
        if self.state_machine.current_state.name != "executing_modules":
            print("This command is only available in the executing modules state.")
            return
        modules = self.current_storage.get_data("modules")
        if not modules:
            print("No modules to execute.")
            return
        print("Executing modules:")
        for module in modules:
            print(f"Running module: {module}")
            # Here you would typically call the actual module execution
            # For this example, we'll just simulate it
            print(f"Module {module} executed successfully.")
        print("All modules executed.")

    def dummy_agent_action(self, action: str, data: Dict):
        print(f"Agent action: {action}")
        print(f"Data: {json.dumps(data, indent=2)}")

def main():
    ModularCLI().cmdloop()

if __name__ == "__main__":
    main()