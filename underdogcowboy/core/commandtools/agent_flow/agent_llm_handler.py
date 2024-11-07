import os 
import yaml

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
    'assessment': 'assessmentbuilder',
    'leftOff': 'leftOff' 
    # Add other agents here as needed
}

# Load configuration from YAML file
def load_config() -> dict:
    config_path = os.path.join(os.path.dirname(__file__), 'config.yaml')

    with open(config_path, 'r') as file:
        return yaml.safe_load(file)


def send_agent_data_to_llm(llm_config, session_name, agent_name, agent_type, pre_prompt=None, post_prompt=None):
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

def run_category_call(llm_config, session_name, agent_name, agent_type, pre_prompt=None, post_prompt=None):

    from underdogcowboy import AgentDialogManager
    from state_management.json_storage_manager import JSONStorageManager

    
    config = load_config()
    base_dir = config['storage']['base_dir']


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
        session_file = os.path.join(base_dir, f"{session_name}.json")
        session_file = os.path.expanduser(session_file)
        screen_name = "AgentAssessmentBuilderScreen" # hardcoded for now. 

        if not os.path.exists(session_file):
            return f"Error: Session file for '{session_name}' not found."

        # Load JSON data from the session file
        with open(session_file, 'r') as file:
            session_data = json.load(file)

        # Check if 'screens' exists in session_data
        if 'screens' not in session_data:
            session_data['screens'] = {}
            logging.info(f"'screens' key not found in session data. Initialized 'screens'.")

        # Check if the specified screen_name exists
        if screen_name not in session_data['screens']:
            session_data['screens'][screen_name] = {
                "data": {
                    "agents": {}
                },
                "meta": {}
            }
            logging.info(f"Screen '{screen_name}' not found in session data. Initialized '{screen_name}'.")

            # Save the modified session data back to the JSON file
            with open(session_file, 'w') as file:
                json.dump(session_data, file, indent=4)

        # Ensure the agent entry exists within the specified screen's data
        if agent_name not in session_data['screens'][screen_name]["data"]["agents"]:
            # Initialize the agent entry with an empty categories list
            session_data['screens'][screen_name]["data"]["agents"][agent_name] = {
                "categories": [],
                "meta_notes": "",
                "base_agent": agent_name
            }

            # Save the modified session data back to the JSON file
            with open(session_file, 'w') as file:
                json.dump(session_data, file, indent=4)

        # Now retrieve the current storage for categories
        current_storage = session_data['screens'][screen_name]["data"]["agents"][agent_name]["categories"]

        assessment_structure["categories"] = current_storage

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

def run_category_description_change(llm_config, agent_name, agent_type, category_to_change, session_name):
    from underdogcowboy import AgentDialogManager
    import json
    import os

    config = load_config()
    base_dir = config['storage']['base_dir']
    agents_dir = os.path.expanduser("~/.underdogcowboy/agents")

    agent_file = os.path.join(agents_dir, f"{agent_name}.json")
    if not os.path.exists(agent_file):
        return f"Error: Agent file for '{agent_name}' not found."
    
    with open(agent_file, 'r') as f:
        agent_data = json.load(f)

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

    # Initialize the agent and process the prompt
    model_id = llm_config['model_id']
    adm = AgentDialogManager([agent], model_name=model_id)

    # Load session file
    session_file = os.path.expanduser(os.path.join(base_dir, f"{session_name}.json"))
    screen_name = "AgentAssessmentBuilderScreen"
    
    if not os.path.exists(session_file):
        return f"Error: Session file for '{session_name}' not found."
    
    # Load session data and retrieve the current categories
    with open(session_file, 'r') as file:
        session_data = json.load(file)
    
    current_categories = session_data.get('screens', {}).get(screen_name, {}).get("data", {}).get("agents", {}).get(agent_name, {}).get("categories", [])

    # Define the prompt with enriched context including agent history
    prompt = f"""
    Analyze the following agent definition and its current categories. Then suggest a new description specifically for the category '{category_to_change}'.

    Agent Definition:
    {json.dumps(agent_data, indent=2)}
    
    Current Categories with Titles:
    {json.dumps([{cat['name']: cat.get('title', '')} for cat in current_categories], indent=2)}
    
    Change only the description of '{category_to_change}', maintaining its original purpose and context while ensuring it aligns well with other categories.

    Return your response in the following JSON format:
    {{
        "new_description": "Suggested New Description"
    }}
    """
    
    # Request a response
    response = agent >> prompt
    
    # Define the expected keys for our JSON structure
    expected_keys = ["new_description"]

    # Create an instance of JSONExtractor
    extractor = JSONExtractor(response.text, expected_keys)

    # Extract and parse the JSON
    json_data, inspection_data = extractor.extract_and_parse_json()

    # Define expected inspection data
    expected_inspection_data = {
        'number_of_keys': 1,
        'keys': ["new_description"],
        'values_presence': {"new_description": True},
        'keys_match': True
    }

    # Check the inspection data against the expected data
    is_correct, deviations = extractor.check_inspection_data(expected_inspection_data)

    if is_correct:
        logging.info("New description extracted successfully.")
        new_description = json_data["new_description"]
        return new_description
    else:
        logging.info("Error in extracting. Deviations found:")
        logging.info(deviations)
        logging.info("Raw response:")
        logging.info(response.text)

def run_category_title_change(llm_config, agent_name, agent_type, category_to_change, session_name):
    from underdogcowboy import AgentDialogManager
    import json
    import os

    config = load_config()
    base_dir = config['storage']['base_dir']
    agents_dir = os.path.expanduser("~/.underdogcowboy/agents")

    agent_file = os.path.join(agents_dir, f"{agent_name}.json")
    if not os.path.exists(agent_file):
        return f"Error: Agent file for '{agent_name}' not found."
    
    with open(agent_file, 'r') as f:
        agent_data = json.load(f)

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

    
    # Initialize the agent and process the prompt
    model_id = llm_config['model_id']
    adm = AgentDialogManager([agent], model_name=model_id)
   
    
    # Load session file
    session_file = os.path.expanduser(os.path.join(base_dir, f"{session_name}.json"))
    screen_name = "AgentAssessmentBuilderScreen"
    
    if not os.path.exists(session_file):
        return f"Error: Session file for '{session_name}' not found."
    
    # Load session data and retrieve the current categories
    with open(session_file, 'r') as file:
        session_data = json.load(file)
    
    current_categories = session_data.get('screens', {}).get(screen_name, {}).get("data", {}).get("agents", {}).get(agent_name, {}).get("categories", [])
        
    
    # Define the prompt with enriched context including agent history
    prompt = f"""
    Analyze the following agent definition and its current categories. Then suggest a new title specifically for the category '{category_to_change}'.
    
    Agent Definition:
    {json.dumps(agent_data, indent=2)}
    
    Current Categories with Descriptions:
    {json.dumps([{cat['name']: cat.get('description', '')} for cat in current_categories], indent=2)}
    
    Change only the title of '{category_to_change}', maintaining its original purpose and context while ensuring it aligns well with other categories.

    Return your response in the following JSON format:
    {{
        "new_title": "Suggested New Title"
    }}
    """
      
    # Request a response
    response = agent >> prompt
    
    # Define the expected keys for our JSON structure
    expected_keys = ["new_title"]

    # Create an instance of JSONExtractor
    extractor = JSONExtractor(response.text, expected_keys)

    # Extract and parse the JSON
    json_data, inspection_data = extractor.extract_and_parse_json()

    # Define expected inspection data
    expected_inspection_data = {
        'number_of_keys': 1,
        'keys': ["new_title"],
        'values_presence': {"new_title": True},
        'keys_match': True
    }

    # Check the inspection data against the expected data
    is_correct, deviations = extractor.check_inspection_data(expected_inspection_data)

    if is_correct:
        logging.info("New title extracted successfully.")
        new_title = json_data["new_title"]
        return new_title
    else:
        logging.info("Error in extracting. Deviations found:")
        logging.info(deviations)
        logging.info("Raw response:")
        logging.info(response.text)

def run_scale_call(llm_config, agent_name, agent_type, category_to_change, session_name):
    """
    Retrieves 5 scales (title and description) for a selected category using the LLM.

    Args:
        llm_config (dict): Configuration for the LLM, including model_id.
        agent_name (str): Name of the agent.
        agent_type (str): Type of the agent.
        selected_category (str): The category for which to retrieve scales.
        session_name: Name of the session the user is doing the work in. 
    Returns:
        dict or str: Updated assessment_structure with scales or an error message.
    """
    from underdogcowboy import AgentDialogManager
    import json
    import os

    config = load_config()
    base_dir = config['storage']['base_dir']
    session_file = os.path.expanduser(os.path.join(base_dir, f"{session_name}.json"))
    screen_name = "AgentAssessmentBuilderScreen"
    
    if not os.path.exists(session_file):
        return f"Error: Session file for '{session_name}' not found."
    
    # Load session data and retrieve the current categories
    with open(session_file, 'r') as file:
        session_data = json.load(file)
 
    current_categories = session_data.get('screens', {}).get(screen_name, {}).get("data", {}).get("agents", {}).get(agent_name, {}).get("categories", [])
   

    # Ensure the agent_type exists in the registry
    if agent_type not in AGENT_REGISTRY:
        return f"Error: Invalid agent type '{agent_type}' specified."

    logging.info(f"Agent type involved: {agent_type}")
    logging.info(f"Agent name: {agent_name}")
    logging.info(f"Selected category: {category_to_change}")

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

        model_id = llm_config['model_id']
        adm = AgentDialogManager([agent], model_name=model_id)

        agents_dir = os.path.expanduser("~/.underdogcowboy/agents")
        agent_file = os.path.join(agents_dir, f"{agent_name}.json")

        if not os.path.exists(agent_file):
            return f"Error: Agent file for '{agent_name}' not found."

        with open(agent_file, 'r') as f:
            agent_data = json.load(f)

        # Ensure the selected category exists in the current assessment_structure
        # Here, you might need to load the existing assessment_structure if it's stored
        # For simplicity, we'll assume categories are already present in agent_data or elsewhere

        prompt = f"""
        You are tasked with creating assessment scales for a specific category.
        For the category "{category_to_change}", please suggest 5 scales.
        Each scale should have a "name" and a "description".

        this are the current Categories with Descriptions for reference in your analysis:
        {json.dumps([{cat['name']: cat.get('description', '')} for cat in current_categories], indent=2)}
  
        Return your response in the following JSON format:
        {{
            "scales": [
                {{"name": "Scale1", "description": "Description of Scale1"}},
                ... (repeat for 5 scales)
            ]
        }}
        Agent definition: {json.dumps(agent_data)}
        """

        response = agent >> prompt
        logging.info("Scale retrieval complete. Extracting scales...")

        # Define the expected keys for our JSON structure
        expected_keys = ["scales"]

        # Create an instance of JSONExtractor
        extractor = JSONExtractor(response.text, expected_keys)

        # Extract and parse the JSON
        json_data, inspection_data = extractor.extract_and_parse_json()

        # Define expected inspection data
        expected_inspection_data = {
            'number_of_keys': 1,
            'keys': ["scales"],
            'values_presence': {"scales": True},
            'keys_match': True
        }

        # Check the inspection data against the expected data
        is_correct, deviations = extractor.check_inspection_data(expected_inspection_data)

        if is_correct:
            logging.info("Scales extracted successfully.")
            scales = json_data["scales"]
            for scale in scales:
                scale["fixed"] = False


            logging.info(f"Returning the updated assessment_structure with scales: {scales}")
            return scales

        else:
            logging.info("Error in extracting scales. Deviations found:")
            logging.info(deviations)
            logging.info("Raw response:")
            logging.info(response.text)
            return "Error: Failed to extract scales correctly."

    except Exception as e:
        logging.error("Exception occurred in run_scale_call", exc_info=True)
        return f"Error: {str(e)}"

def run_leftoff_summary(llm_config, agent_type, aggregate_files_path, session_name):
    
    import json
    import os

    from underdogcowboy import AgentDialogManager
    from underdogcowboy.core.tools.work_session_tools import aggregate_files 
    
    # Ensure the agent_type exists in the registry
    if agent_type not in AGENT_REGISTRY:
        return f"Error: Invalid agent type '{agent_type}' specified."

    logging.info(f"Agent type involved: {agent_type}")
  
    # Dynamically import the correct agent from the registry
    try:
        agent_module = __import__('underdogcowboy', fromlist=[AGENT_REGISTRY[agent_type]])
        agent = getattr(agent_module, AGENT_REGISTRY[agent_type])
    except ImportError as e:
        logging.error("Agent Registry ImportError", exc_info=True)
        return f"Error: Could not import the specified agent '{agent_type}'. {str(e)}"

    config = load_config()
    base_dir = config['storage']['base_dir']
    session_file = os.path.expanduser(os.path.join(base_dir, f"{session_name}.json"))
    screen_name = "WorkSessionScreen"
    
    if not os.path.exists(session_file):
        return f"Error: Session file for '{session_name}' not found."
    
    # Load session data
    with open(session_file, 'r') as file:
        session_data = json.load(file)
 
    model_id = llm_config['model_id']
    adm = AgentDialogManager([agent], model_name=model_id)

    adm | [agent]

    refs = aggregate_files(aggregate_files_path)

    response = agent >> f"file {refs[0]}"
    response = agent >> f"file {refs[1]}"
    response = agent >> "Can you give a 5 sentence summary of your findings?"
    return response.text


def generate_system_prompt(llm_config, agent_name, agent_type, pre_prompt=None, post_prompt=None):
    """
    Generates the final system prompt based on the assessment structure.

    Parameters:
    - llm_config: Configuration for the LLM, including model details.
    - agent_name: The name of the agent whose assessment structure will be loaded.
    - agent_type: The type of agent to handle the evaluation (e.g., 'assessment').
    - pre_prompt: Optional text to prepend to the assessment structure in the prompt.
    - post_prompt: Optional text to append to the prompt.

    Returns:
    - The generated system prompt as a string, or an error message.
    """
    # Ensure the agent_type exists in the registry
    if agent_type not in AGENT_REGISTRY:
        return f"Error: Invalid agent type '{agent_type}' specified."

    # Dynamically import the correct agent from the registry
    try:
        agent_module = __import__('underdogcowboy', fromlist=[AGENT_REGISTRY[agent_type]])
        agent = getattr(agent_module, AGENT_REGISTRY[agent_type])
    except ImportError as e:
        logging.error("Agent Registry ImportError", exc_info=True)
        return f"Error: Could not import the specified agent '{agent_type}'. {str(e)}"

    try:
        from underdogcowboy import AgentDialogManager

        model_id = llm_config['model_id']
        adm = AgentDialogManager([agent], model_name=model_id)
        logging.info("Created AgentDialogManager instance.")

        # Load assessment structure
        assessments_dir = os.path.expanduser("~/.underdogcowboy/assessments")
        assessment_file = os.path.join(assessments_dir, f"assess_{agent_name}")
        if not os.path.exists(assessment_file):
            return f"Error: Assessment file 'assess_{agent_name}' not found."

        with open(assessment_file, 'r') as f:
            assessment_structure = json.load(f)

        # Construct the prompt
        if pre_prompt:
            prompt = pre_prompt
            prompt += f"\nAssessment structure: {json.dumps(assessment_structure)}"
        else:
            prompt = f"Generate a system prompt for an assessment agent based on this structure: {json.dumps(assessment_structure)}"

        if post_prompt:
            prompt += f"\n{post_prompt}"

        # Send the prompt to the LLM via the selected agent
        response = agent >> prompt
        logging.info("System prompt generated successfully.")

        return response.text

    except Exception as e:
        logging.error(f"Error generating system prompt: {str(e)}", exc_info=True)
        return f"Error: {str(e)}"