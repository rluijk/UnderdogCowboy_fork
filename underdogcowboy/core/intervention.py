from .timeline_editor import CommandProcessor

class InterventionManager:
    def __init__(self, dialog_manager):
        self.dialog_manager = dialog_manager

    def allow_intervention(self, condition=True):
        """
        Checks if intervention is allowed based on a condition.
        Defaults to always allowing intervention.
        """
        return condition

    def get_input(self):
        """
        Gets user input from the command line.
        You can customize this for more sophisticated input methods.
        """
        user_input = input("Intervention! Enter message (or 'resume' to continue): ")
        return user_input

    def intervene(self):
        """
        Manages the intervention process, including multi-turn dialogue and command mode.
        """
        if self.dialog_manager.__class__.__name__ == "AgentDialogManager":    
            active_entity = self.dialog_manager.active_agent
            if active_entity is None:
                print("No active agent for intervention.")
                return

            def process_command(command):
                # Assuming active_agent has a process_command method
                self.dialog_manager.active_agent.process_command(command)

        elif self.dialog_manager.__class__.__name__ == "BasicDialogManager":
            active_entity = self.dialog_manager.get_active_processor()
            if active_entity is None:
                print("No active dialog for intervention.")
                return

            def process_command(command):
                active_entity.process_command(command)

        else:
            print("Unsupported DialogManager type for intervention.")
            return

        while True:
            user_input = self.get_input()

            if user_input.lower() == "resume":
                print("Resuming script execution.")
                break
            elif user_input.lower() == "cmd":
                print("Entering command mode. Type 'interactive' to return.")
                while True:
                    command = input("Command Mode> ")
                    if command.lower() == 'interactive':
                        print("Returning to interactive mode.")
                        break
                    else:
                        process_command(command)  # Call the appropriate process_command function
            else:
                # Generate and add the agent's response
                agent_response = self.dialog_manager.message(active_entity, user_input)
                print(f"Agent: {agent_response}")