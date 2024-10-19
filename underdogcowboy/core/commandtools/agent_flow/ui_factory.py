import logging

class UIFactory:
    def __init__(self, screen_instance):
        """Initialize UIFactory with a reference to the screen instance."""
        self.screen = screen_instance

    def ui_factory(self, id: str):
        """Returns the appropriate UI component or action based on button ID."""
        ui_class, action = self.get_ui_and_action(id)
        return ui_class, action

    def get_ui_and_action(self, id: str):
        """Maps ID to UI class and action function."""
        if id == "load-session":
            # Delay import to avoid circular imports and import the UI component directly
            from ui_components.load_session_ui import LoadSessionUI
            ui_class = LoadSessionUI
            action_func = None
        elif id == "new-agent-button":
            from ui_components.new_agent_ui import NewAgentUI
            ui_class = NewAgentUI
        elif id == "new-dialog_button":
            from ui_components.new_dialog_ui import NewDialogUI
            ui_class = NewDialogUI
        elif id == "new-button":
            # Delay import for the new session UI
            from ui_components.new_session_ui import NewSessionUI
            ui_class = NewSessionUI
            action_func = None
        elif id == "chat-gui":  
            ui_class = self.create_chat_ui  
            action_func = None            
        elif id == "cancel-load-session":
            from ui_components.center_content_ui import CenterContent
            ui_class = CenterContent
            action_func = None                
        elif id == "system-message":
            # Delay import for system message UI
            from ui_components.system_message_ui import SystemMessageUI
            ui_class = SystemMessageUI
            action_func = None
        elif id == "confirm-session-load":
            # Action is handled in the screen instance
            ui_class = None
            action_func = getattr(self.screen, "transition_to_analysis_ready", None)
        else:
            raise ValueError(f"Unknown  ID: {id}. Make sure the ID is mapped in 'get_ui_and_action'.")

        logging.info(f"Resolving UI class: {ui_class.__name__ if ui_class else None}, Action function: {action_func.__name__ if action_func else None}")

        if not action_func and not ui_class:
            raise ValueError(f"No UI or action found for  ID: {id}")

        return ui_class, action_func

    def create_chat_ui(self, name: str, type: str, processor=None):  
            """Factory method to create the appropriate ChatUI."""  
            from ui_components.chat_ui import ChatUI,  DialogChatUI, AgentChatUI  
            
            if type == "dialog":  
                return DialogChatUI(name, type, processor)  
            if type == "agent":
                return AgentChatUI(name, type, processor)  
            else:  
                return ChatUI(name, type, processor) 