import logging
import os
import json

from datetime import datetime


from textual.app import ComposeResult   
from textual.widgets import Static, Button, ListView, Label, ListItem
from textual.containers import Container, Vertical

from rich.text import Text

from events.dialog_events import DialogSelected
from events.button_events import UIButtonPressed

# UI
from ui_components.autoselect_list_view_ui import AutoSelectListView

# UC
from underdogcowboy.core.config_manager import LLMConfigManager 

import platform

def is_windows():
    return platform.system() == "Windows"


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
        # Get dialogs from the file system
        config_manager: LLMConfigManager = LLMConfigManager()
        dialogs_dir: str = config_manager.get_general_config().get('dialog_save_path', '')

        # Check if the folder exists, so we can switch to different dialog paths easily.
        if not os.path.exists(dialogs_dir):
            os.makedirs(dialogs_dir, exist_ok=True)

        dialogs = sorted([f for f in os.listdir(dialogs_dir) if f.endswith('.json')], key=str.lower)

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
            
            # Calculate the maximum length of dialog names
            max_name_length = max(len(f.replace('.json', '')) for f in dialogs)
            # Define the padding length to create space between name and dates
            padding_length = max(max_name_length + 2, 20)  # Minimum padding of 20

            for dialog_file in dialogs:
                # Get the dialog name without the .json extension
                dialog_name = dialog_file.replace('.json', '')

                # Get the full path of the dialog file
                file_path = os.path.join(dialogs_dir, dialog_file)
                
                # Get the creation and modification times and format them
                creation_time = os.path.getctime(file_path)
                formatted_creation_time = datetime.fromtimestamp(creation_time).strftime("%Y-%m-%d %H:%M:%S")
                modification_time = os.path.getmtime(file_path)
                formatted_modification_time = datetime.fromtimestamp(modification_time).strftime("%Y-%m-%d %H:%M:%S")
                
                # Create a string with the dialog name, padded to the defined length
                padded_name = dialog_name.ljust(padding_length)
                dialog_info = (
                    f"{padded_name} Created: {formatted_creation_time} | "
                    f"Modified: {formatted_modification_time}"
                )
                
                list_view.append(ListItem(Label(dialog_name)))
            
        # Enable the load button if there are dialogs
        load_button.disabled = False


    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "load-button":
            selected_item = self.query_one("#dialog-list").highlighted_child
            if selected_item:
                selected_dialog = selected_item.children[0].render()  # Get the text from the Label

                if is_windows():
                    # win fix?
                    selected_dialog = selected_dialog._renderable.plain
                else:
                    selected_dialog = selected_dialog.plain


                logging.info(f"Load button pressed, selected dialog: {selected_dialog}")
                self.post_message(DialogSelected(selected_dialog))
        elif event.button.id == "cancel-button":
            self.post_message(UIButtonPressed("cancel-load-session"))
            
