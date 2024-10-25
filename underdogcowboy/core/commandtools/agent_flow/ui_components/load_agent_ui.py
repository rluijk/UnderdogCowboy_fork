import logging
import os
import json

from datetime import datetime

from textual.app import ComposeResult   
from textual.widgets import Static, Button, ListView, Label, ListItem
from textual.containers import Container, Vertical

from rich.text import Text


from events.agent_events import AgentSelected
from events.button_events import UIButtonPressed


from ui_components.autoselect_list_view_ui import AutoSelectListView

class LoadAgentUI(Static):
    """A UI for getting an agent selected for the build-in agent to assess"""
    def compose(self):
        yield Container(
            Vertical(
                Static("Select a agent to load:", id="agent-prompt", classes="agent-prompt"),
                AutoSelectListView(id="agent-list", classes="agent-list"),
                Label("No agent available. Create a new agent first.", id="no-agents-label", classes="hidden"),
                Button("Load Selected Agent", id="load-button", disabled=True, classes="action-button"),
                Button("Cancel", id="cancel-button", classes="action-button")
            ),
            id="centered-box", classes="centered-box"
        )

    def on_mount(self):
        self.load_agents()


    def on_list_view_highlighted(self, event: AutoSelectListView.Highlighted):
        self.query_one("#load-button").disabled = False



    def load_agents(self):
        agents_dir = os.path.expanduser("~/.underdogcowboy/agents")

        if not os.path.exists(agents_dir):
            os.makedirs(agents_dir)

        agents = sorted([f for f in os.listdir(agents_dir) if f.endswith('.json')], key=str.lower)

        list_view = self.query_one("#agent-list", AutoSelectListView)
        no_agents_label = self.query_one("#no-agents-label")
        load_button = self.query_one("#load-button")

        list_view.clear()
        
        if not agents:
            list_view.display = False
            no_agents_label.remove_class("hidden")
            load_button.disabled = True
        else:
            list_view.display = True
            no_agents_label.add_class("hidden")
            
            # Calculate the maximum length of agent names
            max_name_length = max(len(f.replace('.json', '')) for f in agents)
            # Define the padding length to create space between name and dates
            padding_length = max(max_name_length + 2, 20)  # Minimum padding of 20

            for agent_file in agents:
                # Get the agent name without the .json extension
                agent_name = agent_file.replace('.json', '')

                # Get the full path of the agent file
                file_path = os.path.join(agents_dir, agent_file)
                
                # Get the creation and modification times and format them
                creation_time = os.path.getctime(file_path)
                formatted_creation_time = datetime.fromtimestamp(creation_time).strftime("%Y-%m-%d %H:%M:%S")
                modification_time = os.path.getmtime(file_path)
                formatted_modification_time = datetime.fromtimestamp(modification_time).strftime("%Y-%m-%d %H:%M:%S")
                
                # Create a string with the agent name, padded to the defined length
                padded_name = agent_name.ljust(padding_length)
                agent_info = (
                    f"{padded_name} Created: {formatted_creation_time} | "
                    f"Modified: {formatted_modification_time}"
                )
                
                list_view.append(ListItem(Label(agent_name)))
            
        # Enable the load button if there are agents
        load_button.disabled = False


    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "load-button":
            selected_item = self.query_one("#agent-list").highlighted_child
            if selected_item:
                selected_agent = selected_item.children[0].render()  # Get the text from the Label
                logging.info(f"Load button pressed, selected agent: {selected_agent}")
                self.post_message(AgentSelected(selected_agent))
        elif event.button.id == "cancel-button":
            self.post_message(UIButtonPressed("cancel-load-session"))
            
