from textual import on
from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.widgets import Footer, Label, ListItem, ListView
from textual.widgets import Static, Input, Button, Label, Checkbox
import asyncio

# Events
from events.category_events import CategoryLoaded


class CategoryEditorUI(Static):

    def __init__(self, session_manager):
        super().__init__()
        self.session_manager = session_manager  # Store session manager for persistence
        self.selected_category = self.session_manager.get_data('selected_category', "Default Category")
        self.styles.overflow_y = "auto"  # Enable vertical scrolling
        self.styles.height = "500"       # Set a fixed height

    def compose(self) -> ComposeResult:
        """Compose the UI for category editing."""
        
        # ListView containing multiple ListItems for each row
        with ListView(id="category-editor"):
            # Section Header
            yield ListItem(Label(f"Editing Category: {self.selected_category}", id="section-header", classes="section-header"))

            # Category Name and Refresh Section
            yield ListItem(
                Horizontal(
                    Button("R", id="refresh-name", classes="refresh-button compact-button"),
                    Input(placeholder="Enter category name...", id="category-name", classes="category-input compact-input"),
                    Label("Category Name:", classes="label-fixed compact-label")
                )
            )

            # Category Description and Refresh Section
            yield ListItem(
                Horizontal(
                    Button("R", id="refresh-desc", classes="refresh-button compact-button"),
                    Input(placeholder="Enter category description...", id="category-desc", classes="category-input compact-input"),
                    Label("Category Description:", classes="label-fixed compact-label")
                )
            )

            # 5-Point Scale Fields Header
            yield ListItem(Label("Define 5-Point Scale:", classes="section-header"))

            # 5-Point Scale Fields (each scale is a row)
            for i in range(1, 6):
                # Scale Title Section
                yield ListItem(
                    Horizontal(
                        Button("R", id=f"refresh-scale{i}-title", classes="refresh-button compact-button"),
                        Input(placeholder=f"Enter Scale {i} Title...", id=f"scale{i}-title", classes="category-input compact-input"),
                        Checkbox(label="Fixed", id=f"scale{i}-title-fixed", classes="checkbox-fixed compact-checkbox"),
                        Label(f"Scale {i} Title:", classes="label-fixed compact-label")
                    )
                )

                # Scale Description Section
                yield ListItem(
                    Horizontal(
                        Button("R", id=f"refresh-scale{i}-desc", classes="refresh-button compact-button"),
                        Input(placeholder=f"Enter Scale {i} Description...", id=f"scale{i}-desc", classes="category-input compact-input"),
                        Checkbox(label="Fixed", id=f"scale{i}-desc-fixed", classes="checkbox-fixed compact-checkbox"),
                        Label(f"Scale {i} Description:", classes="label-fixed compact-label")
                    )
                )

            # Refresh All Unfixed Button Section
            yield ListItem(
                Button("Refresh All Unfixed", id="refresh-all-unfixed", classes="refresh-button large-button")
            )

            # Back to Categories Button Section
            yield ListItem(
                Button("Back to Categories", id="back-to-list", classes="back-button large-button")
            )

    @on(CategoryLoaded)
    def handle_category_selected(self, event: CategoryLoaded) -> None:
        """Handle category loaded event and update UI accordingly."""
        self.selected_category = event.category_name
        self.query_one("#section-header", Label).update(f"Editing Category: {self.selected_category}")

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
        """Refresh the field (category name or description) asynchronously."""
        input_field = self.query_one(f"#{field_id}", Input)
        await self.set_button_loading_state(f"refresh-{field_id}")  # Show loading state

        # Simulate a delay for refresh operation to show async behavior
        await asyncio.sleep(1)

        # Update field value and session data
        input_field.value = f"Refreshed {field_id}"
        self.session_manager.update_data(field_id, input_field.value)

        # Reset button state after processing
        await self.reset_button_state(f"refresh-{field_id}")

    async def refresh_scale(self, button_id):
        """Refresh a scale field asynchronously based on button ID."""
        scale_type = button_id.split("-")[2]  # Get 'title' or 'desc'
        scale_number = button_id.split("-")[1]  # Get scale number (1, 2, 3, etc.)
        field_id = f"scale{scale_number}-{scale_type}"
        input_field = self.query_one(f"#{field_id}", Input)

        # Check if the field is fixed
        fixed_checkbox = self.query_one(f"#{field_id}-fixed", Checkbox)
        if fixed_checkbox.value:  # If fixed, do nothing
            return

        await self.set_button_loading_state(button_id)  # Show loading state

        # Simulate a delay for refresh operation
        await asyncio.sleep(1)

        # Update field value and session data
        input_field.value = f"Refreshed {field_id}"
        self.session_manager.update_data(field_id, input_field.value)

        # Reset button state after processing
        await self.reset_button_state(button_id)

    async def refresh_all_unfixed(self):
        """Refresh all non-fixed values for scales asynchronously."""
        for i in range(1, 6):
            for field_type in ["title", "desc"]:
                field_id = f"scale{i}-{field_type}"
                fixed_checkbox = self.query_one(f"#{field_id}-fixed", Checkbox)
                if not fixed_checkbox.value:  # Only refresh if not fixed
                    await self.refresh_scale(f"refresh-scale{i}-{field_type}")

    async def set_button_loading_state(self, button_id):
        """Set button to loading state to indicate an operation is in progress."""
        button = self.query_one(f"#{button_id}", Button)
        button.label = "Loading..."
        button.disabled = True
        await asyncio.sleep(0)  # Yield control to the event loop to apply UI changes immediately

    async def reset_button_state(self, button_id):
        """Reset button to its default state after operation completes."""
        button = self.query_one(f"#{button_id}", Button)
        button.label = button.id.split("-")[-1].capitalize()  # Reset to original label, e.g., "Refresh"
        button.disabled = False
