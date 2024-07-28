from underdogcowboy import Agent

class CommitPromoAgent(Agent):
    def __init__(self, filename, package, is_user_defined=False):
        super().__init__(filename, package, is_user_defined)
        
    def dummy_def():
        pass


SPECIALIZED_AGENTS = {
    "commit_promo": CommitPromoAgent,
    # Add more mappings here for other specialized agents
}