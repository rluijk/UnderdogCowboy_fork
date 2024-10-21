from textual.widgets import ListView

class AutoSelectListView(ListView):
    def on_mount(self) -> None:
        self.index = 0  # Select the first item