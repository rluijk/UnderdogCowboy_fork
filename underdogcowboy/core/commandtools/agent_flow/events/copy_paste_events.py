from textual.message import Message


class LLMResultReceived(Message):
    def __init__(self, sender, result: str):
        super().__init__()
        self.sender = sender
        self.result = result

class CopyToClipboard(Message):
    def __init__(self, content: str):
        super().__init__()
        self.content = content

class CopySpecificContent(Message):
    def __init__(self, content: str):
        super().__init__()
        self.content = content        