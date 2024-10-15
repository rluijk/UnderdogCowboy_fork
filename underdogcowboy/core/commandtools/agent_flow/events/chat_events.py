from textual.message import Message

class TextSubmitted(Message):
    def __init__(self, text: str):
        super().__init__()
        self.text = text        
