import logging
import os
import json

from textual.app import ComposeResult   
from textual.widgets import Static, Button, ListView, Label, ListItem
from textual.containers import Container, Vertical

from rich.text import Text

from events.dialog_events import DialogSelected
from events.button_events import UIButtonPressed

# UI
from ui_components.autoselect_list_view_ui import AutoSelectListView

# uc
from underdogcowboy.core.config_manager import LLMConfigManager 


class LoadDialogUI(Static):
    """A UI for getting an dialog selected """
    def compose(self):
        yield Container(
            Vertical(
                Static("Select a dialog to load:", id="dialog-prompt", classes="dialog-prompt"),
                AutoSelectListView(id="dialog-list", classes="dialog-list"),
                Label("No dialog available. Create a new dialog first.", id="no-dialogs-label", classes="hidden"),
                Button("Load Selected Dialog", id="load-button", disabled=True, classes="action-button"),
                Button("Cancel", id="cancel-button", classes="action-button")
            ),
            id="centered-box", classes="centered-box"
        )

    def on_mount(self):
        self.load_dialogs()

    def on_list_view_highlighted(self, event: AutoSelectListView.Highlighted):
        self.query_one("#load-button").disabled = False

    def load_dialogs(self):
        # get dialogss from file system
        
        config_manager: LLMConfigManager = LLMConfigManager()
        dialogs_dir: str = config_manager.get_general_config().get('dialog_save_path', '')
      
        dialogs = [f.replace('.json', '') for f in os.listdir(dialogs_dir) if f.endswith('.json')]

        list_view = self.query_one("#dialog-list")

        no_dialogs_label = self.query_one("#no-dialogs-label")
        load_button = self.query_one("#load-button")

        list_view.clear()
        
        if not dialogs:
            list_view.display = False
            no_dialogs_label.remove_class("hidden")
            load_button.disabled = True
        else:
            list_view.display = True
            no_dialogs_label.add_class("hidden")
            for dialog in dialogs:
                list_view.append(ListItem(Label(dialog)))

        load_button.disabled = False


    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "load-button":
            selected_item = self.query_one("#dialog-list").highlighted_child
            if selected_item:
                selected_dialog = selected_item.children[0].render()  # Get the text from the Label
                logging.info(f"Load button pressed, selected dialog: {selected_dialog}")
                self.post_message(DialogSelected(selected_dialog))
        elif event.button.id == "cancel-button":
            self.post_message(UIButtonPressed("cancel-load-session"))
            
