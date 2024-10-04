import logging

from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Header, Footer, Button, DataTable, Input, Label, Static
from textual.events import Key
from textual.message import Message
from textual.reactive import reactive


class CategoryEditorModal(Static):
    """A modal for editing or adding categories with a 5-point scale."""

    def __init__(self, category=None):
        super().__init__()
        self.category = category

    def compose(self) -> ComposeResult:
        yield Vertical(
            # Category Name with Ask Button
            Horizontal(
                Label("Category Name:", classes="label"),
                Input(placeholder="Enter category name", id="name-input"),
                Button("Ask", id="ask-name", variant="primary", classes="ask-button"),
            ),
            # Description with Ask Button
            Horizontal(
                Label("Description:", classes="label"),
                Input(placeholder="Enter description", id="description-input"),
                Button("Ask", id="ask-description", variant="primary", classes="ask-button"),
            ),
            Label("Define 5-Point Scale:", classes="label"),
            # Scale Point 1 with Ask Button
            Horizontal(
                Label("Scale 1 Title:", classes="sub-label"),
                Input(placeholder="Enter title for scale point 1", id="scale1-title"),
                Button("Ask", id="ask-scale1-title", variant="primary", classes="ask-button"),
            ),
            Horizontal(
                Label("Scale 1 Description:", classes="sub-label"),
                Input(placeholder="Enter description for scale point 1", id="scale1-desc"),
                Button("Ask", id="ask-scale1-desc", variant="primary", classes="ask-button"),
            ),
            # Scale Point 2 with Ask Button
            Horizontal(
                Label("Scale 2 Title:", classes="sub-label"),
                Input(placeholder="Enter title for scale point 2", id="scale2-title"),
                Button("Ask", id="ask-scale2-title", variant="primary", classes="ask-button"),
            ),
            Horizontal(
                Label("Scale 2 Description:", classes="sub-label"),
                Input(placeholder="Enter description for scale point 2", id="scale2-desc"),
                Button("Ask", id="ask-scale2-desc", variant="primary", classes="ask-button"),
            ),
            # Scale Point 3 with Ask Button
            Horizontal(
                Label("Scale 3 Title:", classes="sub-label"),
                Input(placeholder="Enter title for scale point 3", id="scale3-title"),
                Button("Ask", id="ask-scale3-title", variant="primary", classes="ask-button"),
            ),
            Horizontal(
                Label("Scale 3 Description:", classes="sub-label"),
                Input(placeholder="Enter description for scale point 3", id="scale3-desc"),
                Button("Ask", id="ask-scale3-desc", variant="primary", classes="ask-button"),
            ),
            # Scale Point 4 with Ask Button
            Horizontal(
                Label("Scale 4 Title:", classes="sub-label"),
                Input(placeholder="Enter title for scale point 4", id="scale4-title"),
                Button("Ask", id="ask-scale4-title", variant="primary", classes="ask-button"),
            ),
            Horizontal(
                Label("Scale 4 Description:", classes="sub-label"),
                Input(placeholder="Enter description for scale point 4", id="scale4-desc"),
                Button("Ask", id="ask-scale4-desc", variant="primary", classes="ask-button"),
            ),
            # Scale Point 5 with Ask Button
            Horizontal(
                Label("Scale 5 Title:", classes="sub-label"),
                Input(placeholder="Enter title for scale point 5", id="scale5-title"),
                Button("Ask", id="ask-scale5-title", variant="primary", classes="ask-button"),
            ),
            Horizontal(
                Label("Scale 5 Description:", classes="sub-label"),
                Input(placeholder="Enter description for scale point 5", id="scale5-desc"),
                Button("Ask", id="ask-scale5-desc", variant="primary", classes="ask-button"),
            ),
            # Save and Cancel Buttons
            Horizontal(
                Button("Save", variant="success", id="save"),
                Button("Cancel", variant="error", id="cancel"),
            ),
            id="editor-modal"
        )

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses within the modal."""
        if event.button.id.startswith("ask-"):
            await self.handle_ask(event.button.id)
        elif event.button.id == "save":
            await self.handle_save()
        elif event.button.id == "cancel":
            await self.remove()  # Hide the modal

    async def handle_ask(self, button_id: str) -> None:
        """Handle the 'Ask' button presses to generate suggestions."""
        # Map button IDs to corresponding input fields
        field_mapping = {
            "ask-name": "name-input",
            "ask-description": "description-input",
            "ask-scale1-title": "scale1-title",
            "ask-scale1-desc": "scale1-desc",
            "ask-scale2-title": "scale2-title",
            "ask-scale2-desc": "scale2-desc",
            "ask-scale3-title": "scale3-title",
            "ask-scale3-desc": "scale3-desc",
            "ask-scale4-title": "scale4-title",
            "ask-scale4-desc": "scale4-desc",
            "ask-scale5-title": "scale5-title",
            "ask-scale5-desc": "scale5-desc",
        }

        input_id = field_mapping.get(button_id)
        if not input_id:
            await self.app.notify("Invalid field for suggestion.", severity="error")
            return

        input_widget = self.query_one(f"#{input_id}", Input)
        field_label = self.get_field_label(input_id)

        # Simulate LLM suggestion (Replace this with actual LLM integration)
        suggestion = f"Suggested {field_label}"

        # Update the input field with the suggestion
        input_widget.value = suggestion
        await self.app.notify(f"Suggested value inserted for {field_label}.", severity="info")

    def get_field_label(self, input_id: str) -> str:
        """Retrieve a human-readable label for the given input ID."""
        label_mapping = {
            "name-input": "Category Name",
            "description-input": "Description",
            "scale1-title": "Scale 1 Title",
            "scale1-desc": "Scale 1 Description",
            "scale2-title": "Scale 2 Title",
            "scale2-desc": "Scale 2 Description",
            "scale3-title": "Scale 3 Title",
            "scale3-desc": "Scale 3 Description",
            "scale4-title": "Scale 4 Title",
            "scale4-desc": "Scale 4 Description",
            "scale5-title": "Scale 5 Title",
            "scale5-desc": "Scale 5 Description",
        }
        return label_mapping.get(input_id, "Field")

    async def handle_save(self) -> None:
        """Handle the save action."""
        name = self.query_one("#name-input", Input).value.strip()
        description = self.query_one("#description-input", Input).value.strip()
        scale_titles = [
            self.query_one("#scale1-title", Input).value.strip(),
            self.query_one("#scale2-title", Input).value.strip(),
            self.query_one("#scale3-title", Input).value.strip(),
            self.query_one("#scale4-title", Input).value.strip(),
            self.query_one("#scale5-title", Input).value.strip(),
        ]
        scale_descriptions = [
            self.query_one("#scale1-desc", Input).value.strip(),
            self.query_one("#scale2-desc", Input).value.strip(),
            self.query_one("#scale3-desc", Input).value.strip(),
            self.query_one("#scale4-desc", Input).value.strip(),
            self.query_one("#scale5-desc", Input).value.strip(),
        ]

        # Validation
        if not name:
            await self.app.notify("Category Name is required.", severity="error")
            return
        for i in range(5):
            if not scale_titles[i]:
                await self.app.notify(f"Scale {i+1} Title is required.", severity="error")
                return
            if not scale_descriptions[i]:
                await self.app.notify(f"Scale {i+1} Description is required.", severity="error")
                return

        scale_points = [
            {"Title": scale_titles[i], "Description": scale_descriptions[i]}
            for i in range(5)
        ]

        self.emit_no_wait(CategorySaved(name, description, scale_points, self.category))
        await self.remove()  # Hide the modal


class CategorySaved(Message):
    """Message emitted when a category is saved."""

    def __init__(self, name, description, scale_points, original_name=None):
        super().__init__()
        self.name = name
        self.description = description
        self.scale_points = scale_points
        self.original_name = original_name


class CategoryManagementApp(App):
    """A mock interface for Category Management with 5-point scales."""

    CSS = """
    Screen {
        background: #1e1e1e;
        color: #c5c5c5;
    }
    .title {
        padding: 1 0;
        text-align: center;
    }
    .label {
        padding: 1 0;
    }
    .sub-label {
        padding: 1 0;
        margin-left: 1;
    }
    DataTable {
        height: 20;
        width: 100%;
        margin: 1 0 1 0;
    }
    Button {
        width: 20%;
        margin: 1 1 1 1;
    }
    .ask-button {
        width: 8%;
        margin: 1 0 1 1;
    }
    Input {
        width: 60%;  /* Adjust this percentage to control the size of the input fields */
        margin-right: 1;
    }
    #editor-modal {
        width: 100%;
        height: auto;
        background: #2d2d2d;
        color: #c5c5c5;
        border: #444444;
    }
    """

    categories = reactive([
        {
            "Name": "Functionality",
            "Description": "How well the agent performs tasks.",
            "Fixed": True,
            "Scale": 5,
            "ScalePoints": [
                {"Title": "Poor", "Description": "Agent fails to perform basic tasks."},
                {"Title": "Fair", "Description": "Agent performs tasks with some issues."},
                {"Title": "Good", "Description": "Agent performs tasks reliably."},
                {"Title": "Very Good", "Description": "Agent performs tasks efficiently."},
                {"Title": "Excellent", "Description": "Agent exceeds task performance expectations."},
            ]
        },
        {
            "Name": "Usability",
            "Description": "Ease of use and user experience.",
            "Fixed": False,
            "Scale": 5,
            "ScalePoints": [
                {"Title": "Difficult", "Description": "User struggles to interact with the agent."},
                {"Title": "Moderate", "Description": "User faces some challenges when interacting."},
                {"Title": "Easy", "Description": "User interacts with the agent without issues."},
                {"Title": "Very Easy", "Description": "User finds interaction smooth and intuitive."},
                {"Title": "Seamless", "Description": "User experiences flawless interaction."},
            ]
        },
        {
            "Name": "Reliability",
            "Description": "Consistency and dependability.",
            "Fixed": True,
            "Scale": 5,
            "ScalePoints": [
                {"Title": "Unreliable", "Description": "Agent frequently fails or crashes."},
                {"Title": "Inconsistent", "Description": "Agent performance varies significantly."},
                {"Title": "Dependable", "Description": "Agent performs consistently under normal conditions."},
                {"Title": "Highly Dependable", "Description": "Agent maintains performance even under stress."},
                {"Title": "Exceptionally Reliable", "Description": "Agent consistently performs flawlessly."},
            ]
        },
    ])

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static("Category Management", classes="title")
        yield DataTable(id="category-table")
        with Horizontal():
            yield Button("Toggle Fixed", id="toggle-fixed", variant="primary")
            yield Button("Define Category", id="define-category", variant="primary")
            yield Button("Add New Category", id="add-category", variant="success")
        yield Footer()

    async def on_mount(self) -> None:
        self.table = self.query_one(DataTable)
        self.table.add_columns("Name", "Description", "Fixed", "Scale")
        self.refresh_table()

    def refresh_table(self):
        self.table.clear()
        for category in self.categories:
            fixed_status = "✅" if category["Fixed"] else "❌"
            self.table.add_row(
                category["Name"],
                category["Description"],
                fixed_status,
                str(category["Scale"])
            )

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "toggle-fixed":
            await self.toggle_fixed()
        elif event.button.id == "define-category":
            await self.define_category()
        elif event.button.id == "add-category":
            await self.add_category()

    async def toggle_fixed(self):
        selected = self.table.cursor_row
        if selected is None:
            await self.notify("Please select a category to toggle.", severity="warning")
            return
        category = self.categories[selected]
        category["Fixed"] = not category["Fixed"]
        self.refresh_table()
        status = "fixed" if category["Fixed"] else "unfixed"
        await self.notify(f'Category "{category["Name"]}" is now {status}.', severity="success")

    async def define_category(self):
        selected = self.table.cursor_row
        if selected is None:
            await self.notify("Please select a category to define.", severity="warning")
            return
        category = self.categories[selected]
        modal = CategoryEditorModal(category=category["Name"])
        # Pre-fill the modal inputs
        await self.mount(modal)
        modal.query_one("#name-input", Input).value = category["Name"]
        modal.query_one("#description-input", Input).value = category["Description"]
        # Pre-fill scale points
        for i in range(5):
            modal.query_one(f"#scale{i+1}-title", Input).value = category["ScalePoints"][i]["Title"]
            modal.query_one(f"#scale{i+1}-desc", Input).value = category["ScalePoints"][i]["Description"]

    async def add_category(self):
        modal = CategoryEditorModal()
        await self.mount(modal)

    async def on_category_saved(self, message: CategorySaved) -> None:
        if message.original_name:
            # Update existing category
            for cat in self.categories:
                if cat["Name"] == message.original_name:
                    cat["Name"] = message.name
                    cat["Description"] = message.description
                    cat["ScalePoints"] = message.scale_points
                    break
            await self.notify(f'Category "{message.original_name}" updated successfully.', severity="success")
        else:
            # Add new category
            self.categories.append({
                "Name": message.name,
                "Description": message.description,
                "Fixed": False,
                "Scale": 5,
                "ScalePoints": message.scale_points
            })
            await self.notify(f'New category "{message.name}" added successfully.', severity="success")
        self.refresh_table()

    async def on_message(self, message: Message) -> None:
        if isinstance(message, CategorySaved):
            await self.on_category_saved(message)

    async def on_key(self, event: Key) -> None:
        if event.key == "q":
            await self.action_quit()


if __name__ == "__main__":
    CategoryManagementApp().run()
