import logging
import os
import json

from textual.app import ComposeResult   
from textual.widgets import Static, Button, ListView, Label, ListItem
from textual.containers import Container, Vertical

from rich.text import Text


from events.agent_events import AgentSelected
from events.button_events import UIButtonPressed


class LoadAgentUI(Static):
    """A UI for getting an agent selected for the build-in agent to assess"""
    def compose(self):
        yield Container(
            Vertical(
                Static("Select a agent to load:", id="agent-prompt", classes="agent-prompt"),
                ListView(id="agent-list", classes="agent-list"),
                Label("No agent available. Create a new agent first.", id="no-agents-label", classes="hidden"),
                Button("Load Selected Agent", id="load-button", disabled=True, classes="action-button"),
                Button("Cancel", id="cancel-button", classes="action-button")
            ),
            id="centered-box", classes="centered-box"
        )

    def on_mount(self):
        self.load_agents()

    def on_list_view_selected(self, event: ListView.Selected):
        self.query_one("#load-button").disabled = False

    def load_agents(self):
        # get agents from file system
        
        agents_dir = os.path.expanduser("~/.underdogcowboy/agents")
        agents = [f.replace('.json', '') for f in os.listdir(agents_dir) if f.endswith('.json')]

        list_view = self.query_one("#agent-list")

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
            for agent in agents:
                list_view.append(ListItem(Label(agent)))


    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "load-button":
            selected_item = self.query_one("#agent-list").highlighted_child
            if selected_item:
                selected_agent = selected_item.children[0].render()  # Get the text from the Label
                logging.info(f"Load button pressed, selected agent: {selected_agent}")
                self.post_message(AgentSelected(selected_agent))
        elif event.button.id == "cancel-button":
            self.post_message(UIButtonPressed("cancel-load-session"))
            
