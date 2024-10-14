from textual.message import Message


class AppReadyProcessor(Message):
    def __init__(self,remark: str):
        self.remark = remark
        super().__init__()

