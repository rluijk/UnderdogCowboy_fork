from underdogcowboy import adm, agentclarity, assessmentbuilder

# Dialog manager, with our two meta helpers
adm | [agentclarity,assessmentbuilder]

print(agentclarity >> "what is your goal?")