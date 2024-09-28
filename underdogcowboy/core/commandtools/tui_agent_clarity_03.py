from typing import Dict, List, Set
from textual.app import App, ComposeResult

from textual.widgets import Button, Static, Label, Header, Footer, Input, ListItem, TextArea
from textual.containers import Grid, Vertical, Horizontal, Container
from textual.widgets import Placeholder, Collapsible, ListView
from textual.message import Message
from textual import on

import logging

from uccli import StateMachine, State, StorageManager

#  Clear existing handlers and set up logging to a file
for handler in logging.root.handlers[:]:
    logging.root.removeHandler(handler)

logging.basicConfig(
    filename='app_03.log', 
    level=logging.DEBUG, 
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class SystemMessageUI(Static):
    """A UI for creating and submitting a system message."""
        
    def compose(self) -> ComposeResult:
        # Retrieve any existing system message from the storage manager
        stored_message = self.app.storage_manager.get_data("system_message")
        if stored_message is None:
            stored_message = ""  # Set to empty if no message is found


        
        # Create the UI layout with a text area, submit, and cancel buttons
        with Vertical(id="system-message-container"):
            yield Label("Enter your system message:")
            yield TextArea(id="system-message-input", text=stored_message)  # Pre-populate if there's a stored message
            yield Button("Submit", id="submit-system-message", classes="action-button")
            yield Button("Cancel", id="cancel-system-message", classes="action-button")

    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "submit-system-message":
            # Retrieve the message from the text area
            system_message = self.query_one("#system-message-input").text
            # Log and store the system message
            logging.info(f"System message submitted: {system_message}")
            self.app.storage_manager.update_data("system_message", system_message)
            
            # Clear the UI after submission by posting a message
            self.app.query_one(DynamicContainer).clear_content()
            self.app.notify("System message stored successfully.")
        
        elif event.button.id == "cancel-system-message":
            # Post a message instead of clearing the UI directly, ensuring consistency
            self.post_message(UIButtonPressed("cancel-system-message"))




class DynamicContainer(Static):
    """A container to dynamically load UI elements."""
    def clear_content(self):
        """Clear all current content."""
        self.remove_children()

    def load_content(self, widget: Static):
        """Load a new widget into the container."""
        self.mount(widget)

class SessionSelected(Message):
    def __init__(self, session_name: str):
        self.session_name = session_name
        logging.info(f"SessionSelected message created with session_name: {session_name}")
        super().__init__()

class NewSessionCreated(Message):
    def __init__(self, session_name: str):
        self.session_name = session_name
        super().__init__()

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

class NewSessionUI(Static):
    """A UI for creating a new session."""

    def compose(self):
        yield Vertical(
            Static("Create a new session:", id="new-session-prompt"),
            Label("Enter a name for the new session:", id="session-name-label"),
            Input(placeholder="Session name", id="session-name-input"),
            Button("Create Session", id="create-button", disabled=True),
            Button("Cancel", id="cancel-button")
        )

    def on_mount(self):
        self.query_one("#session-name-input").focus()

    def on_input_changed(self, event: Input.Changed):
        if event.input.id == "session-name-input":
            self.query_one("#create-button").disabled = len(event.value.strip()) == 0

    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "create-button":
            session_name = self.query_one("#session-name-input").value.strip()
            if session_name:
                self.post_message(NewSessionCreated(session_name))
        elif event.button.id == "cancel-button":
            self.post_message(UIButtonPressed("cancel-new-session"))

class LoadUI(Static):
    """A simple UI that is loaded dynamically upon clicking 'Load'."""
    def compose(self) -> ComposeResult:
        yield Button("Confirm Load", id="confirm-load-button")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "confirm-load-button":
            self.parent.post_message(UIButtonPressed("confirm-load"))

class NewUI(Static):
    def compose(self) -> ComposeResult:
        yield Button("Confirm Analyze", id="confirm-analyze-button")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "confirm-analyze-button":
            self.parent.post_message(UIButtonPressed("confirm-analyze"))

class StateInfo(Static):
    def compose(self) -> ComposeResult:
        yield Label("Current State:", id="state-label")
        yield Label("", id="current-state")
        yield Label("Available Actions:", id="actions-label")
        yield Label("", id="available-actions")
        yield Label("Current Action:", id="action-label")
        yield Label("", id="current-action")
     
    def update_state_info(self, state_machine: StateMachine, current_action: str = ""):
        self.query_one("#current-state").update(state_machine.current_state.name)
        self.query_one("#current-action").update(current_action)
        available_actions = ", ".join(state_machine.get_available_commands())
        self.query_one("#available-actions").update(available_actions)

class ActionSelected(Message):
    def __init__(self, action: str):
        self.action = action
        super().__init__()

class StateButtonGrid(Static):
    def __init__(self, state_machine: StateMachine, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.state_machine = state_machine
        self.all_actions = self.get_ordered_actions()

    def get_ordered_actions(self) -> List[str]:
        all_actions = set()
        for state in self.state_machine.states.values():
            all_actions.update(state.transitions.keys())

        ordered_actions = []
        visited_states = set()
        state_queue = [self.state_machine.current_state]

        while state_queue:
            current_state = state_queue.pop(0)
            if current_state.name in visited_states:
                continue
            visited_states.add(current_state.name)

            state_actions = list(current_state.transitions.keys())
            ordered_actions.extend([action for action in state_actions if action not in ordered_actions])

            for action, next_state in current_state.transitions.items():
                if next_state.name not in visited_states:
                    state_queue.append(next_state)

        ordered_actions.extend([action for action in all_actions if action not in ordered_actions])

        return ordered_actions

    def compose(self) -> ComposeResult:
        with Grid(id="button-grid"):
            for action in self.all_actions:
                yield Button(str(action), id=f"btn-{action}", classes="action-button")

    def on_mount(self) -> None:
        self.update_buttons()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        action = str(event.button.label)
        if self.state_machine.transition(action):
            logging.info(f"Action '{action}' executed. New state: {self.state_machine.current_state.name}")
            self.post_message(ActionSelected(action))  # Emit custom event
        else:
            logging.warning(f"Action '{action}' is not allowed in current state: {self.state_machine.current_state.name}")

        self.update_buttons()
        self.parent.query_one(StateInfo).update_state_info(self.state_machine, action)

    def update_buttons(self) -> None:
        allowed_actions = self.state_machine.get_available_commands()
        for button in self.query("Button"):
            action = str(button.label)
            button.disabled = action not in allowed_actions

class CenterContent(Static):
    def __init__(self, action: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.action = action

    def compose(self) -> ComposeResult:
        yield Label(f"Content for action: {self.action}")

class UIButtonPressed(Message):
    def __init__(self, button_id: str):
        self.button_id = button_id
        super().__init__()

class LeftSideButtons(Container):
    def compose(self) -> ComposeResult:
        with Grid(id="left-side-buttons", classes="left-side-buttons"):
            yield Button("New", id="new-button", classes="left-side-button")
            yield Button("Load", id="load-session", classes="left-side-button")
            yield Button("List", id="list-button", classes="left-side-button")
            yield Button("Save", id="save-button", classes="left-side-button")
            yield Button("Config", id="config-button", classes="left-side-button")
            yield Button("Model", id="model-button", classes="left-side-button")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.post_message(UIButtonPressed(event.button.id))

class LeftSideContainer(Container):
    def compose(self) -> ComposeResult:
        yield LeftSideButtons()

class MainApp(App):
    CSS_PATH = "state_machine_app.css"
            
    def __init__(self, state_machine: StateMachine, storage_manager: StorageManager, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.state_machine = state_machine
        self.storage_manager = storage_manager
        self.current_storage = None
        self.title = "Agent Clarity"  # Set an initial title for the app
        

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(id="agent-centre", classes="dynamic-spacer"):
            yield LeftSideContainer(classes="left-dynamic-spacer")
            yield DynamicContainer(id="center-dynamic-container", classes="center-dynamic-spacer")
            yield Placeholder("right", classes="right-dynamic-spacer")

        with Vertical(id="app-layout"):
            with Collapsible(title="Task Panel", id="state-info-collapsible", collapsed=False):
                yield StateInfo(id="state-info")
                yield StateButtonGrid(self.state_machine, id="button-grid")
        
        yield Footer(id="footer", name="footer")

    def on_mount(self) -> None:
        logging.info("MainApp on_mount called")
        self.query_one(StateInfo).update_state_info(self.state_machine, "")
        self.update_header()  # Initialize the header
        self.log_header_state()  # Log initial header state

    def update_header(self, session_name=None):
        if session_name:
            self.sub_title = f"Active Session: {session_name}"
            logging.info(f"Updated app sub_title with session name: {session_name}")
        else:
            self.sub_title = ""
            logging.info("Cleared app sub_title")
        
        # Force a refresh of the entire app
        self.refresh(layout=True)

    def log_header_state(self):
        logging.info(f"Current app title: {self.title}")
        logging.info(f"Current app sub_title: {self.sub_title}")


    def on_session_selected(self, event: SessionSelected):
        try:
            self.current_storage = self.storage_manager.load_session(event.session_name)
            self.notify(f"Session '{event.session_name}' loaded successfully")
            self.query_one(DynamicContainer).clear_content()
            
            # Retrieve the stored state from the session
            stored_state = self.current_storage.get_data("current_state")
            if stored_state and stored_state in self.state_machine.states:
                self.state_machine.current_state = self.state_machine.states[stored_state]
            else:
                # If no stored state or invalid state, set to a default state
                # TODO this would be need to be set via the CLI config, since this is dependd on the specific CLI 
                self.state_machine.current_state = self.state_machine.states["analysis_ready"]
            
            # Use existing method to update UI
            self.query_one(StateInfo).update_state_info(self.state_machine, "")
            self.query_one(StateButtonGrid).update_buttons()
            
            # Update header with session name
            logging.info(f"Attempting to update header with session name: {event.session_name}")
            self.update_header(event.session_name)
            self.log_header_state()  # Log the header state after update
            
            # test code (can remove when committed)
            # self.storage_manager.update_data("analysis", "some analysis data")
            

        except ValueError as e:
            logging.error(f"Error loading session: {str(e)}")
            self.notify(f"Error loading session: {str(e)}", severity="error")

    def ui_factory(self, button_id: str):
        ui_class, action = self.get_ui_and_action(button_id)
        return ui_class, action

    def get_ui_and_action(self, button_id: str):
        # Map button ID to UI class and action function
        if button_id == "load-session":
            ui_class_name = "LoadSessionUI"
            action_func_name = None
        elif button_id == "new-button":
            ui_class_name = "NewSessionUI"
            action_func_name = None
        elif button_id == "system-message":  # Handling system message button
            ui_class_name = "SystemMessageUI"
            action_func_name = None    
        elif button_id == "confirm-session-load":
            ui_class_name = None
            action_func_name = "transition_to_analysis_ready"
        else:
            raise ValueError(f"Unknown button ID: {button_id}. Hint: Ensure that this button ID is mapped correctly in 'get_ui_and_action'.")

        logging.info(f"Resolving UI class: {ui_class_name}, Action function: {action_func_name}")

        # Get the UI class and action function
        ui_class = globals().get(ui_class_name) if ui_class_name else None
        action_func = getattr(self, action_func_name, None) if action_func_name else None

        if not action_func and not ui_class:
            raise ValueError(f"No UI or action found for button ID: {button_id}")

        return ui_class, action_func

    def transition_to_agent_loaded(self) -> None:
        agent_loaded_state = self.state_machine.states.get("agent_loaded")
        if agent_loaded_state:
            self.state_machine.current_state = agent_loaded_state
            logging.info(f"Set state to agent_loaded")
            self.query_one(StateInfo).update_state_info(self.state_machine, "")
            self.query_one(StateButtonGrid).update_buttons()
        else:
            logging.error(f"Failed to set state to agent_loaded: State not found")

    def transition_to_analyse_state(self) -> None:
        analyse_state = self.state_machine.states.get("analysis_ready")
        if analyse_state:
            self.state_machine.current_state = analyse_state
            logging.info(f"Set state to analysis_ready")
            self.query_one(StateInfo).update_state_info(self.state_machine, "")
            self.query_one(StateButtonGrid).update_buttons()
        else:
            logging.error(f"Failed to set state to analysis_ready: State not found")

    def transition_to_analysis_ready(self) -> None:
        analysis_ready_state = self.state_machine.states.get("analysis_ready")
        if analysis_ready_state:
            self.state_machine.current_state = analysis_ready_state
            logging.info(f"Set state to analysis_ready")
            self.query_one(StateInfo).update_state_info(self.state_machine, "")
            self.query_one(StateButtonGrid).update_buttons()
            
            # Store the current state in the session
            if self.current_storage:
                self.storage_manager.save_current_session(self.current_storage)
        else:
            logging.error(f"Failed to set state to analysis_ready: State not found")

    def clear_session(self):
        self.current_storage = None
        self.update_header()
        self.log_header_state()  # Log the header state after clearing

    def on_new_session_created(self, event: NewSessionCreated):
        try:
            self.current_storage = self.storage_manager.create_session(event.session_name)
            self.notify(f"New session '{event.session_name}' created successfully")
            self.query_one(DynamicContainer).clear_content()
            self.transition_to_analysis_ready()
            
            logging.info(f"Attempting to update header with new session name: {event.session_name}")
            self.update_header(event.session_name)
            self.log_header_state()  # Log the header state after update
        except ValueError as e:
            logging.error(f"Error creating session: {str(e)}")
            self.notify(f"Error creating session: {str(e)}", severity="error")

    @on(UIButtonPressed)
    def handle_ui_button_pressed(self, event: UIButtonPressed) -> None:
        logging.debug(f"Handler 'handle_ui_button_pressed' invoked with button_id: {event.button_id}")
        dynamic_container = self.query_one(DynamicContainer)
        dynamic_container.clear_content()

        try:
            # Use the UI factory to get the corresponding UI and action
            ui_class, action = self.ui_factory(event.button_id)
            
            # Load the UI component if it exists (for "load-session")
            if ui_class:
                if event.button_id == "load-session" and not self.storage_manager.list_sessions():
                    self.notify("No sessions available. Create a new session first.", severity="warning")
                else:
                    dynamic_container.load_content(ui_class())

            # Handle the action (state change) only if there's an action function
            if action:
                action()

        except ValueError as e:
            logging.error(f"Error: {e}")


    def on_action_selected(self, event: ActionSelected) -> None:
        if event.action == "reset":
                self.clear_session()
        
        dynamic_container = self.query_one(DynamicContainer)
        dynamic_container.clear_content()

        if event.action == "system_message":
            # Load SystemMessageUI instead of just displaying a label
            dynamic_container.mount(SystemMessageUI())
        else:
            # For other actions, load generic content as before
            dynamic_container.mount(CenterContent(event.action))

  

def create_state_machine() -> StateMachine:
    # Define states
    initial_state = State("initial")
    agent_created_state = State("agent_created")
    agent_loaded_state = State("agent_loaded")
    model_selected_state = State("model_selected")
    analysis_ready_state = State("analysis_ready")

    # Define transitions
    initial_state.add_transition("load_agent", agent_loaded_state)
    initial_state.add_transition("create_agent", agent_created_state)
    initial_state.add_transition("list_models", initial_state)

    agent_created_state.add_transition("load_agent", agent_loaded_state)

    agent_loaded_state.add_transition("load_agent", agent_loaded_state)
    agent_loaded_state.add_transition("select_model", model_selected_state)
    agent_loaded_state.add_transition("system_message", agent_loaded_state)
    agent_loaded_state.add_transition("list_models", agent_loaded_state)

    model_selected_state.add_transition("load_agent", agent_loaded_state)
    model_selected_state.add_transition("select_model", model_selected_state)
    model_selected_state.add_transition("analyze", analysis_ready_state)
    model_selected_state.add_transition("system_message", model_selected_state)

    analysis_ready_state.add_transition("load_agent", agent_loaded_state)
    analysis_ready_state.add_transition("select_model", model_selected_state)
    analysis_ready_state.add_transition("analyze", analysis_ready_state)
    analysis_ready_state.add_transition("export_analysis", analysis_ready_state)
    analysis_ready_state.add_transition("feedback", analysis_ready_state)
    analysis_ready_state.add_transition("feedback_input", analysis_ready_state)
    analysis_ready_state.add_transition("feedback_output", analysis_ready_state)
    analysis_ready_state.add_transition("feedback_rules", analysis_ready_state)
    analysis_ready_state.add_transition("feedback_constraints", analysis_ready_state)
    analysis_ready_state.add_transition("system_message", analysis_ready_state)

    # Add reset transition to all states
    for state in [agent_created_state, agent_loaded_state, model_selected_state, analysis_ready_state]:
        state.add_transition("reset", initial_state)

    # Create state machine
    state_machine = StateMachine(initial_state)
    for state in [agent_created_state, agent_loaded_state, model_selected_state, analysis_ready_state]:
        state_machine.add_state(state)

    return state_machine

def main():
    state_machine = create_state_machine()  # Initialize state machine first
    storage_manager = StorageManager("~/.tui_agent_clarity_03")
    
    # Now create the app, but don't pass the app reference to the state machine yet
    app = MainApp(state_machine, storage_manager)
    
    # Inject the app reference into the state machine after initialization
    state_machine.app = app
    
    # Run the app
    app.run()

if __name__ == "__main__":
    main()    