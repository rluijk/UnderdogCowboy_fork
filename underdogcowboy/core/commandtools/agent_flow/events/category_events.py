from textual.message import Message

class CategorySelected(Message):
    """Message emitted when a category is selected."""
    def __init__(self, category_name: str):
        super().__init__()
        self.category_name = category_name

class CategoryLoaded(Message):
    """Message emitted when a category is selected and MOVED to display of the category."""
    def __init__(self, category_name: str):
        super().__init__()
        self

class CategoryDataUpdate(Message):
    def __init__(self):
        super().__init__()

class ScalesUpdated(Message):
    def __init__(self):
        super().__init__()
