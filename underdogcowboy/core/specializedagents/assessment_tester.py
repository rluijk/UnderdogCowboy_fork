
import os
import re
import sys
import subprocess
import shutil

import time
import uuid
from typing import Optional, Any, Union

from underdogcowboy import Agent

import os
# print(f"AssessmentTestAgent file path: {os.path.abspath(__file__)}")

class AssessmentTestAgent(Agent):
    """
    Tester Agent
    """
    def __init__(self, filename: str, package: str, is_user_defined: bool = False) -> None:
        super().__init__(filename, package, is_user_defined)
        self.response: Optional[str] = None
    
    def assess(self, msg: str, model_name: str = "anthropic") -> bool:
        return False
        #self.register_with_dialog_manager(AgentDialogManager([self], model_name))
        #self.response = self.message(msg)    
        
        # send the response to a llm validation agent, that check if this is a proper response and let it return a confidence interval in json
        # parse the json out the response with the JsonExtractor
        # check the json for the confidence interval, if higher than 95% set to true, else to false.

        '''
        val_response = validation_agent >> self.response
        confidence _interval = val_response | jsonExtractor
        if confidence _interval["confidence"] > 95:
            return true
        else:
            return False    
        '''

        
        # return the bool and the response that has the recommendations and report 

    def __or__(self, other):
        print("__or__ from assessment_tester.py")
        if isinstance(other, str):
            return self.assess(other)
        return NotImplemented        
    

