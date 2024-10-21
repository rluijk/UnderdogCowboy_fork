# agent_llm_handler.py
import os 
import logging
import json
"""
This module provides functions for dynamically selecting agents and sending
agent data (like agent history) to the selected agent for processing via LLM.

AGENT_REGISTRY is a mapping of agent names (or types) to their respective classes or objects.
The agents process or evaluate agent data, typically sent as JSON, and return
a response based on the agent's specific logic (such as 'clarity' for agent assessment).
"""

# Mapping agent names to agent classes (or objects)
AGENT_REGISTRY = {
    'clarity': 'agentclarity',
    'assessment': 'assessmentbuilder'
    # Add other agents here as needed
}

def send_agent_data_to_llm(llm_config, agent_name, agent_type, pre_prompt=None, post_prompt=None):
    """
    Calls the LLM via a dynamically selected agent with the agent's data included in the prompt.

    This function takes the LLM configuration, agent name, and the agent type (from the registry),
    then constructs a prompt by combining any pre-prompt, the agent's data (loaded from a file),
    and an optional post-prompt. It sends this information to the selected agent for evaluation
    or feedback, depending on the nature of the agent.

    Parameters:
    - llm_config: Configuration for the LLM, including model details.
    - agent_name: The name of the agent whose data will be loaded and sent.
    - agent_type: The type of agent to handle the evaluation (e.g., 'clarity').
    - pre_prompt: Optional text to prepend to the agent data in the prompt.
    - post_prompt: Optional text to append to the agent data in the prompt.
    
    Returns:
    - The response text from the agent (via LLM), or an error message.
    """
    
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

def run_analysis(llm_config, agent_name, pre_prompt=None, post_prompt=None, adm=None):
    """
    Calls the LLM via a dynamically selected agent with the agent's data included in the prompt.

    Parameters:
    - llm_config: Configuration for the LLM, including model details.
    - agent_name: The name of the agent whose data will be loaded and sent.
    - pre_prompt: Optional text to prepend to the agent data in the prompt.
    - post_prompt: Optional text to append to the agent data in the prompt.
    - adm: Optional existing AgentDialogManager instance to reuse.

    Returns:
    - The response text from the agent (via LLM), and the AgentDialogManager instance.
    """
    from underdogcowboy import AgentDialogManager

    logging.info("run_analysis -> running analysis for agent")

    # Ensure the agent_type exists in the registry
    agent_type = 'clarity'  # Set directly since this is specific to clarity
    if agent_type not in AGENT_REGISTRY:
        return f"Error: Invalid agent type '{agent_type}' specified."

    # Dynamically import the correct agent from the registry
    try:
        agent_module = __import__('underdogcowboy', fromlist=[AGENT_REGISTRY[agent_type]])
        agent = getattr(agent_module, AGENT_REGISTRY[agent_type])
    except ImportError as e:
        return f"Error: Could not import the specified agent '{agent_type}'. {str(e)}"

    try:
        if adm is None:
            model_id = llm_config['model_id']
            adm = AgentDialogManager([agent], model_name=model_id)
            logging.info("Created new AgentDialogManager instance.")
        else:
            logging.info("Using existing AgentDialogManager instance.")

        # The agent under analysis
        agents_dir = os.path.expanduser("~/.underdogcowboy/agents")
        agent_file = os.path.join(agents_dir, f"{agent_name}.json")

        if not os.path.exists(agent_file):
            return f"Error: Agent file for '{agent_name}' not found."

        with open(agent_file, 'r') as f:
            agent_data = json.load(f)

        # Construct the prompt dynamically using the optional arguments
        prompt = pre_prompt or "Analyze this agent definition: "
        prompt += json.dumps(agent_data)
        if post_prompt:
            prompt += f" {post_prompt}"

        # Send the constructed prompt to the LLM via the selected agent
        response = agent >> prompt

        # Return both the response text and the AgentDialogManager instance
        return response.text, adm

    except Exception as e:
        return f"Error: {str(e)}"
