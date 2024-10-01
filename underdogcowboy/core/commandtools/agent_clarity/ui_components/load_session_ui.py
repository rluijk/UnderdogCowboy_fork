import logging

from textual.containers import Container, Vertical
from textual.widgets import Button, ListView, Label, Static, ListItem

from events.session_events import SessionSelected
from events.button_events import UIButtonPressed


class LoadSessionUI(Static):
    """A UI for loading sessions, displayed when clicking 'Load'."""

    def compose(self):
        yield Container(
            Vertical(
                Static("Select a session to load:", id="session-prompt", classes="session-prompt"),
                ListView(id="session-list", classes="session-list"),
                Label("No sessions available. Create a new session first.", id="no-sessions-label", classes="hidden"),
                Button("Load Selected Session", id="load-button", disabled=True, classes="action-button"),
                Button("Cancel", id="cancel-button", classes="action-button")
            ),
            id="centered-box", classes="centered-box"
        )

    def on_mount(self):
        self.load_sessions()

    def load_sessions(self):
        sessions = self.app.storage_manager.list_sessions()
        list_view = self.query_one("#session-list")
        no_sessions_label = self.query_one("#no-sessions-label")
        load_button = self.query_one("#load-button")

        list_view.clear()
        
        if not sessions:
            list_view.display = False
            no_sessions_label.remove_class("hidden")
            load_button.disabled = True
        else:
            list_view.display = True
            no_sessions_label.add_class("hidden")
            for session in sessions:
                list_view.append(ListItem(Label(session)))

    def on_list_view_selected(self, event: ListView.Selected):
        self.query_one("#load-button").disabled = False


    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "load-button":
            selected_item = self.query_one("#session-list").highlighted_child
            if selected_item:
                selected_session = selected_item.children[0].render()  # Get the text from the Label
                logging.info(f"Load button pressed, selected session: {selected_session}")
                self.post_message(SessionSelected(selected_session))
        elif event.button.id == "cancel-button":
            self.post_message(UIButtonPressed("cancel-load-session"))
