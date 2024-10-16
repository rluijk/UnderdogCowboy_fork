from textual.widgets import Static


class SessionDependentUI(Static):
    def __init__(self, session_manager, screen_name, agent_name_plain,*args, **kwargs):
        self.session_manager = session_manager
        self.screen_name = screen_name
        self.agent_name_plain = agent_name_plain
        super().__init__(*args, **kwargs)
