# agent_llm_handler.py

""" DUPLICATE 

FOR NOW COMMENTED OUT, BUT THE WORKING AND USED VERSION
HAS THE WRAPPER: run_analysis. 

If this file (which i believe is the duplicate) is needed, please
look how to properly integrate with the correct one. 

IF THIS FILE IS STILL THERE AFTER THE COMMIT, IT CAN BE DELETED

"""



"""
import os 
import json




# Mapping agent names to agent classes (or objects)
AGENT_REGISTRY = {
    'clarity': 'agentclarity',
    # Add other agents here as needed
}

def send_agent_data_to_llm(llm_config, agent_name, agent_type, pre_prompt=None, post_prompt=None):

    
    from underdogcowboy import AgentDialogManager

    # Ensure the agent_type exists in the registry
    if agent_type not in AGENT_REGISTRY:
        return f"Error: Invalid agent type '{agent_type}' specified."

    # Dynamically import the correct agent from the registry
    try:
        agent_module = __import__('underdogcowboy', fromlist=[AGENT_REGISTRY[agent_type]])
        agent = getattr(agent_module, AGENT_REGISTRY[agent_type])
    except ImportError as e:
        return f"Error: Could not import the specified agent '{agent_type}'. {str(e)}"
    
    try:
        model_id = llm_config['model_id']
        adm = AgentDialogManager([agent], model_name=model_id)
        
        agents_dir = os.path.expanduser("~/.underdogcowboy/agents")
        agent_file = os.path.join(agents_dir, f"{agent_name}.json")
        
        if not os.path.exists(agent_file):
            return f"Error: Agent file for '{agent_name}' not found."

        with open(agent_file, 'r') as f:
            agent_data = json.load(f)

        # Construct the prompt dynamically using the optional arguments
        prompt = ""
        if pre_prompt:
            prompt += f"{pre_prompt} "
        
        prompt += json.dumps(agent_data)

        if post_prompt:
            prompt += f" {post_prompt}"

        # Send the constructed prompt to the LLM via the selected agent
        response = agent >> prompt
        return response.text

    except Exception as e:
        return f"Error: {str(e)}"
"""