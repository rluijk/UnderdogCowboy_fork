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

        t = 0 #TODO Remove



class CategorySelected(Message):
    """Custom message to indicate a category has been selected."""
    def __init__(self, sender, category_name: str, category_description: str = ""):
        super().__init__()
        self.sender = sender
        self.category_name = category_name
        self.category_description = category_description  # New field for description