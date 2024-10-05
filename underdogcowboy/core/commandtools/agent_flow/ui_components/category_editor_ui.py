from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Input, Button, Label, Checkbox

class CategoryEditorUI(Vertical):
    """UI component for editing a category with 5-point scale management."""

    def __init__(self, session_manager):
        super().__init__()
        self.session_manager = session_manager  # Store session manager for persistence
        self.selected_category = self.session_manager.get_data('selected_category', "Default Category")

    def compose(self) -> ComposeResult:
        """Compose the UI for category editing."""
        yield Label(f"Editing {self.selected_category}")

        # Category Name and Refresh
        yield Horizontal(
            Vertical(
                Label("Category Name:"),
                Input(placeholder="Category Name", id="category-name"),
                Button("Refresh Name", id="refresh-name"),
            )
        )

        # Category Description and Refresh
        yield Horizontal(
            Vertical(
                Label("Category Description:"),
                Input(placeholder="Category Description", id="category-desc"),
                Button("Refresh Description", id="refresh-desc"),
            )
        )

        # 5-point scale fields
        yield Label("Define 5-Point Scale:")

        for i in range(1, 6):
            # Scale Title and Description for each point
            yield Horizontal(
                Vertical(
                    Label(f"Scale {i} Title:"),
                    Input(placeholder=f"Scale {i} Title", id=f"scale{i}-title"),
                    Checkbox(label="Fixed", id=f"scale{i}-title-fixed"),
                    Button("Refresh", id=f"refresh-scale{i}-title"),
                )
            )
            yield Horizontal(
                Vertical(
                    Label(f"Scale {i} Description:"),
                    Input(placeholder=f"Scale {i} Description", id=f"scale{i}-desc"),
                    Checkbox(label="Fixed", id=f"scale{i}-desc-fixed"),
                    Button("Refresh", id=f"refresh-scale{i}-desc"),
                )
            )

        # Button to refresh all non-fixed values
        yield Button("Refresh All Unfixed", id="refresh-all-unfixed")

        # Button to go back
        yield Button("Back to Categories", id="back-to-list")

    async def on_button_pressed(self, event: Button.Pressed):
        """Handle button presses for refreshing fields or navigating back."""
        button_id = event.button.id
        if button_id == "refresh-name":
            await self.refresh_field("category-name")
        elif button_id == "refresh-desc":
            await self.refresh_field("category-desc")
        elif button_id.startswith("refresh-scale"):
            await self.refresh_scale(button_id)
        elif button_id == "refresh-all-unfixed":
            await self.refresh_all_unfixed()
        elif button_id == "back-to-list":
            await self.app.push_screen("CategoryListScreen")

    async def refresh_field(self, field_id):
        """Simulate refreshing the field (category name or description)."""
        input_field = self.query_one(f"#{field_id}", Input)
        input_field.value = f"Refreshed {field_id}"  # Simulate refresh operation
        self.session_manager.update_data(field_id, input_field.value)

    async def refresh_scale(self, button_id):
        """Simulate refreshing a scale field based on button ID."""
        scale_type = button_id.split("-")[2]  # Get 'title' or 'desc'
        scale_number = button_id.split("-")[1]  # Get scale number (1, 2, 3, etc.)
        field_id = f"scale{scale_number}-{scale_type}"
        input_field = self.query_one(f"#{field_id}", Input)

        # Check if the field is fixed
        fixed_checkbox = self.query_one(f"#{field_id}-fixed", Checkbox)
        if fixed_checkbox.value:  # If fixed, do nothing
            return

        # Simulate refreshing the field
        input_field.value = f"Refreshed {field_id}"
        self.session_manager.update_data(field_id, input_field.value)

    async def refresh_all_unfixed(self):
        """Refresh all non-fixed values for scales."""
        for i in range(1, 6):
            for field_type in ["title", "desc"]:
                field_id = f"scale{i}-{field_type}"
                fixed_checkbox = self.query_one(f"#{field_id}-fixed", Checkbox)
                if not fixed_checkbox.value:  # Only refresh if not fixed
                    input_field = self.query_one(f"#{field_id}", Input)
                    input_field.value = f"Refreshed {field_id}"
                    self.session_manager.update_data(field_id, input_field.value)
