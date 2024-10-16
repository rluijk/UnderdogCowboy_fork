from textual.message import Message
import logging

class LLMCallComplete(Message):
    def __init__(self, sender, input_id, result, adm=None):
        super().__init__()
        self.sender = sender
        self.input_id = input_id
        self.result = result
        self.adm = adm

"""
class LLMCallError(Message):
    def __init__(self, input_id: str, error: str):
        self.input_id = input_id
        self.error = error    
        super().__init__()
        logging.info("LLMCallError Message")
"""
class LLMCallError(Message):
    def __init__(self, sender, input_id, error):
        super().__init__()
        self.sender = sender
        self.input_id = input_id
        self.error = error