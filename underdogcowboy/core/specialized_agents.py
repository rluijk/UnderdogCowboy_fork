import os
from underdogcowboy.core.specializedagents.commit_promo_agent import CommitPromoAgent
from underdogcowboy.core.specializedagents.type_setter_agent import TypeSetterAgent


SPECIALIZED_AGENTS = {
    "commit_promo": CommitPromoAgent,
    "type_maker": TypeSetterAgent,
    # Add more mappings here for other specialized agents
}