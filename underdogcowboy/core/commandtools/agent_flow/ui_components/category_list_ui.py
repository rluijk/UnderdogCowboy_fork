import logging

from textual.containers import Vertical, Container
from textual.widgets import Button, ListView, Label, Static, ListItem
from textual.message import Message

from events.button_events import UIButtonPressed
from events.category_events import CategorySelected
 

class CategoryListUI(Static):
    """UI component for displaying a list of categories with action buttons."""

    def __init__(self):
        super().__init__()
        self.categories = ["Functionality", "Usability", "Reliability", "Scalability", "Security"]  # Mock categories

    def compose(self):
        """Compose the UI for category list view with action buttons."""
        yield Container(
            Vertical(
                Static("Select a Category:", id="category-prompt", classes="category-prompt"),
                ListView(id="category-list", classes="category-list"),
                Label("No categories available.", id="no-categories-label", classes="hidden"),
                Button("Select Category", id="select-button", disabled=True, classes="action-button"),
                Button("Cancel", id="cancel-button", classes="action-button")
            ),
            id="centered-box", classes="centered-box"
        )

    def on_mount(self):
        """Load categories into the list when the UI is mounted."""
        self.load_categories()

    def load_categories(self):
        """Load the list of categories into the ListView."""
        list_view = self.query_one("#category-list")
        no_categories_label = self.query_one("#no-categories-label")
        select_button = self.query_one("#select-button")

        list_view.clear()

        if not self.categories:
            list_view.display = False
            no_categories_label.remove_class("hidden")
            select_button.disabled = True
        else:
            list_view.display = True
            no_categories_label.add_class("hidden")
            for category in self.categories:
                list_view.append(ListItem(Label(category)))

    def on_list_view_selected(self, event: ListView.Selected):
        """Enable the 'Select Category' button when a category is selected."""
        self.query_one("#select-button").disabled = False

    def on_button_pressed(self, event: Button.Pressed):
        """Handle button press events for selecting or canceling."""
        if event.button.id == "select-button":
            selected_item = self.query_one("#category-list").highlighted_child
            if selected_item:
                selected_category = selected_item.children[0].render()  # Get the text from the Label
                # Post the CategorySelected message
                self.post_message(CategorySelected(selected_category.plain))
        elif event.button.id == "cancel-button":
            # Post a UIButtonPressed message for the cancel action
            self.post_message(UIButtonPressed("cancel-category-selection"))

