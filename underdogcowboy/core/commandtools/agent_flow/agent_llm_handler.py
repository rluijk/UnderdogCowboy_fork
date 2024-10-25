import os 
import logging
import json

from typing import Dict

# uc
from underdogcowboy.core.extractor import JSONExtractor

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

    logging.info(f"agent_type involved: {agent_type}")
    logging.info(f"agent name: {agent_name}")

    # Dynamically import the correct agent from the registry
    try:
        agent_module = __import__('underdogcowboy', fromlist=[AGENT_REGISTRY[agent_type]])
        agent = getattr(agent_module, AGENT_REGISTRY[agent_type])
    except ImportError as e:
        logging.error("Agent Registry ImportError", exc_info=True)
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
        logging.debug(f"response: {response}")
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



def run_category_call(llm_config, agent_name, agent_type, pre_prompt=None, post_prompt=None):

    from underdogcowboy import AgentDialogManager

    # Ensure the agent_type exists in the registry
    if agent_type not in AGENT_REGISTRY:
        return f"Error: Invalid agent type '{agent_type}' specified."

    logging.info(f"agent_type involved: {agent_type}")
    logging.info(f"agent name: {agent_name}")

    # Dynamically import the correct agent from the registry
    try:
        agent_module = __import__('underdogcowboy', fromlist=[AGENT_REGISTRY[agent_type]])
        agent = getattr(agent_module, AGENT_REGISTRY[agent_type])
    except ImportError as e:
        logging.error("Agent Registry ImportError", exc_info=True)
        return f"Error: Could not import the specified agent '{agent_type}'. {str(e)}"
    
    try:

        assessment_structure: Dict = {
            "base_agent": "",
            "categories": [],
            "meta_notes": ""
        }

        num_categories = 5

        model_id = llm_config['model_id']
        adm = AgentDialogManager([agent], model_name=model_id)
        
        agents_dir = os.path.expanduser("~/.underdogcowboy/agents")
        agent_file = os.path.join(agents_dir, f"{agent_name}.json")
        
        if not os.path.exists(agent_file):
            return f"Error: Agent file for '{agent_name}' not found."

        with open(agent_file, 'r') as f:
            agent_data = json.load(f)
        
        # Prepare existing fixed categories
        fixed_categories = [cat for cat in assessment_structure["categories"] if cat.get("fixed", False)]
        num_new_categories = num_categories - len(fixed_categories)

        # Instruct the LLM to return categories in a specific JSON format
        prompt = f"""
        Analyze this agent definition and suggest {num_new_categories} new assessment categories for the output it can generate.
        The following categories are already fixed and should not be changed:
        {json.dumps([cat['name'] for cat in fixed_categories])}

        Return your response in the following JSON format:
        {{
            "categories": [
                {{"name": "Category1", "description": "Description of Category1"}},
                ... (repeat for the number of new categories)
            ]
        }}
        Agent definition: {json.dumps(agent_data)}
        """

        logging.info(f"prompt: {prompt}")

        response = agent >> prompt
        print("Analysis complete. Extracting categories...")

        # Define the expected keys for our JSON structure
        expected_keys = ["categories"]

        # Create an instance of JSONExtractor
        extractor = JSONExtractor(response.text, expected_keys)

        # Extract and parse the JSON
        json_data, inspection_data = extractor.extract_and_parse_json()

        # Define expected inspection data
        expected_inspection_data = {
            'number_of_keys': 1,
            'keys': ["categories"],
            'values_presence': {"categories": True},
            'keys_match': True
        }

        # Check the inspection data against the expected data
        is_correct, deviations = extractor.check_inspection_data(expected_inspection_data)

        if is_correct:
            print("Categories extracted successfully.")
            new_categories = json_data["categories"]
            for cat in new_categories:
                cat["fixed"] = False
            assessment_structure["categories"] = fixed_categories + new_categories
            logging.info(f"returning the assessment_structure: {assessment_structure}")
            return assessment_structure

        else:
            print("Error in extracting categories. Deviations found:")
            print(deviations)
            print("Raw response:")
            print(response.text)


    except Exception as e:
        return f"Error: {str(e)}"



    """  """
    try:
        model_name = self.current_model.split(':')[1]
        adm = AgentDialogManager([assessmentbuilder], model_name=model_name)
    except ValueError as e:
        print(f"Error initializing AgentDialogManager: {str(e)}")
        return

    try:
        # Load the agent definition
        with open(self.assessment_structure["base_agent"], 'r') as f:
            agent_data = json.load(f)

        # Prepare existing fixed categories
        fixed_categories = [cat for cat in self.assessment_structure["categories"] if cat.get("fixed", False)]
        num_new_categories = self.num_categories - len(fixed_categories)

        # Instruct the LLM to return categories in a specific JSON format
        prompt = f"""
        Analyze this agent definition and suggest {num_new_categories} new assessment categories for the output it can generate.
        The following categories are already fixed and should not be changed:
        {json.dumps([cat['name'] for cat in fixed_categories])}

        Return your response in the following JSON format:
        {{
            "categories": [
                {{"name": "Category1", "description": "Description of Category1"}},
                ... (repeat for the number of new categories)
            ]
        }}
        Agent definition: {json.dumps(agent_data)}
        """
        
        response = assessmentbuilder >> prompt
        print("Analysis complete. Extracting categories...")

        # Define the expected keys for our JSON structure
        expected_keys = ["categories"]

        # Create an instance of JSONExtractor
        extractor = JSONExtractor(response.text, expected_keys)

        # Extract and parse the JSON
        json_data, inspection_data = extractor.extract_and_parse_json()

        # Define expected inspection data
        expected_inspection_data = {
            'number_of_keys': 1,
            'keys': ["categories"],
            'values_presence': {"categories": True},
            'keys_match': True
        }

        # Check the inspection data against the expected data
        is_correct, deviations = extractor.check_inspection_data(expected_inspection_data)

        if is_correct:
            print("Categories extracted successfully.")
            new_categories = json_data["categories"]
            for cat in new_categories:
                cat["fixed"] = False
            self.assessment_structure["categories"] = fixed_categories + new_categories
            self.do_list_categories(None)
        else:
            print("Error in extracting categories. Deviations found:")
            print(deviations)
            print("Raw response:")
            print(response.text)

    except FileNotFoundError:
        print(f"Agent definition file not found: {self.assessment_structure['base_agent']}")
    except json.JSONDecodeError:
        print(f"Invalid JSON in agent definition file: {self.assessment_structure['base_agent']}")
    except Exception as e:
        print(f"Error during analysis: {str(e)}")
        print("Raw response:")
        print(response.text)    


def do_load():
        # load the correct data structure
        pass 