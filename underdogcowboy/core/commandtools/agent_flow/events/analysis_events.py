from textual.message import Message

class AnalysisCompleteEvent(Message):
    def __init__(self, sender, adm):
        super().__init__()
        self.sender = sender
        self.adm = adm

class AnalysisError(Message):
    def __init__(self, error: str):
        self.error = error
        super().__init__()

"""
TODO: Check if can be removed.

class AnalysisComplete(Message):
    def __init__(self, result: str):
        self.result = result
        super().__init__()

"""