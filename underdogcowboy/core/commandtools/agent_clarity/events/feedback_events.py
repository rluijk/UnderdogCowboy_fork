
from textual.message import Message

# --- Input ---
class FeedbackInputComplete(Message):
    def __init__(self, result: str):
        self.result = result
        super().__init__()

class FeedbackInputError(Message):
    def __init__(self, error: str):
        self.error = error
        super().__init__()

# --- Output ---
class FeedbackOutputComplete(Message):
    def __init__(self, result: str):
        self.result = result
        super().__init__()

class FeedbackOutputError(Message):
    def __init__(self, error: str):
        self.error = error
        super().__init__()

# --- Rules ---
class FeedbackRulesComplete(Message):
    def __init__(self, result: str):
        self.result = result
        super().__init__()

class FeedbackRulesError(Message):
    def __init__(self, error: str):
        self.error = error
        super().__init__()

#---- Constraints ---
class FeedbackConstraintsComplete(Message):
    def __init__(self, result: str):
        self.result = result
        super().__init__()

class FeedbackConstraintsError(Message):
    def __init__(self, error: str):
        self.error = error
        super().__init__()
