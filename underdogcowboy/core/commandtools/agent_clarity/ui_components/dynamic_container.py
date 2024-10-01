from textual.widgets import  Static


class DynamicContainer(Static):
    """A container to dynamically load UI elements."""
    def clear_content(self):
        """Clear all current content."""
        self.remove_children()

    def load_content(self, widget: Static):
        """Load a new widget into the container."""
        self.mount(widget)
