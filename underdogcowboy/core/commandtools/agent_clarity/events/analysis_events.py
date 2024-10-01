from textual.message import Message

class AnalysisComplete(Message):
    def __init__(self, result: str):
        self.result = result
        super().__init__()

class AnalysisError(Message):
    def __init__(self, error: str):
        self.error = error
        super().__init__()
