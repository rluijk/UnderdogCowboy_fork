from textual.message import Message
import logging

class LLMCallComplete(Message):
    def __init__(self, input_id: str, result: str):
        self.input_id = input_id
        self.result = result    
        super().__init__()
        logging.info("LLMCallComplete Message")
        
class LLMCallError(Message):
    def __init__(self, input_id: str, error: str):
        self.input_id = input_id
        self.error = error    
        super().__init__()
        logging.info("LLMCallError Message")

