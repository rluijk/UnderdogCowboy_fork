
import os
import re
import sys
import subprocess
import shutil

import time
import uuid
from typing import Optional, Any

from underdogcowboy import Agent, DialogManager


class TypeSetterAgent(Agent):
    """
    An agent class for adding type annotations to Python code and managing the associated Git workflow.

    This agent processes Python code, adds type annotations, and manages the Git workflow for 
    reviewing and merging the changes. It interacts with a language model to generate type annotations 
    and handles the creation of temporary files and Git operations.

    Expected output:
    - Processed Python code with added type annotations
    - A new Git branch with the changes
    - A Git merge operation initiated for review

    The agent performs the following main tasks:
    1. Generates type annotations for given Python code using a language model
    2. Cleans and extracts the annotated code from the LLM response
    3. Saves the annotated code to a temporary file
    4. Creates a new Git branch and commits the changes
    5. Initiates a Git merge operation for review

    The resulting Git diff can be used to review and finalize the type annotations.
    """
    def __init__(self, filename: str, package: str, is_user_defined: bool = False) -> None:
        super().__init__(filename, package, is_user_defined)
        self.response: Optional[str] = None
        

    """ LLM """

    def create_typed_diff(self, repo_path: str, file_ref: str, model_name: str = "anthropic") -> None:
        self.register_with_dialog_manager(DialogManager([self], model_name))
        self.response = self.message(file_ref)
        


        # parse out the python from the response.
        cleaned_code = self.clean_llm_response(self.response)

        # Generate a unique identifier
        unique_id: str = f"{int(time.time())}_{uuid.uuid4().hex[:8]}"

        # Use the unique identifier in the filename
        filename: str = f"type-concept_{unique_id}"

        changed_file_path = self.save_response(cleaned_code, filename)
    
        self.git_diff_workflow(repo_path,file_ref,changed_file_path)

        return


    """" TOOLS """

    def clean_llm_response(self,response: str) -> str:
        """
        Clean the LLM response by extracting the Python code within ```python ``` blocks.
        
        Args:
        response (str): The raw response from the LLM.
        
        Returns:
        str: The cleaned Python code.
        
        Raises:
        ValueError: If no Python code block is found or if multiple code blocks are present.
        """
        try:
            # Use regex to find content between ```python and ``` tags
            pattern = r"```python\s*(.*?)\s*```"
            matches = re.findall(pattern, response, re.DOTALL)
            
            if not matches:
                raise ValueError("No Python code block found in the LLM response.")
            
            if len(matches) > 1:
                raise ValueError("Multiple Python code blocks found. Expected only one.")
            
            # Extract the Python code
            python_code = matches[0].strip()
            
            # Validate that the extracted content looks like Python code
            if not python_code or not any(keyword in python_code for keyword in ['def', 'class', 'import', 'from']):
                raise ValueError("Extracted content doesn't appear to be valid Python code.")
            
            return python_code
        
        except re.error as e:
            raise ValueError(f"Error in regex pattern: {str(e)}")
        except Exception as e:
            raise ValueError(f"Unexpected error while cleaning LLM response: {str(e)}")

    def save_response(self, msg: str, filename: str) -> str:
       
        # Create a directory for temporary files if it doesn't exist
        temp_dir = os.path.join(os.getcwd(), 'temp_files')
        os.makedirs(temp_dir, exist_ok=True)

        # Create the full path for the new file
        file_path = os.path.join(temp_dir, filename)

        # Write the message content to the file
        with open(file_path, 'w') as file:
            file.write(msg)

        print(f"Response saved to: {file_path}")
        return file_path  

    def git_diff_workflow(self,repo_path, file_path, changed_file_path):
        # Change to the repository directory
        os.chdir(repo_path)

        # Get the current branch name
        current_branch = self.run_command("git rev-parse --abbrev-ref HEAD")

        # Create a new branch for the changed file
        change_branch = "changetest-" + os.path.basename(file_path)
        self.run_command(f"git checkout -b {change_branch}")

        # Copy the changed file to the repository
        shutil.copy2(changed_file_path, file_path)

        # Stage and commit the changed file
        self.run_command(f"git add {file_path}")
        self.run_command(f'git commit -m "Add changes to {os.path.basename(file_path)}"')

        # Switch back to the original branch
        self.run_command(f"git checkout {current_branch}")

        # Start the merge operation
        self.run_command(f"git merge --no-commit --no-ff {change_branch}")

        print(f"Merge initiated. Please resolve conflicts (if any) and complete the merge.")
        print(f"You can now use 'git diff' to see the changes.")

    def run_command(self,command):
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        output, error = process.communicate()
        if process.returncode != 0:
            print(f"Error executing command: {command}")
            print(error.decode('utf-8'))
            sys.exit(1)
        return output.decode('utf-8').strip()