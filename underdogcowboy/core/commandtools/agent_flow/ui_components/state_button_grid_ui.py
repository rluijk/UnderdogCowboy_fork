import logging
from typing import List

from textual import on
from textual.app import ComposeResult
from textual.widgets import Static, Button
from textual.containers import Grid
from uccli import StateMachine
from state_machines.state_ui import UIState

# UI
from ui_components.state_info_ui import StateInfo

# Events
from events.action_events import ActionSelected
from events.session_events import SessionStateChanged


import importlib.util
import os

def dynamic_import(file_path: str, function_name: str, parameters: dict):
    """
    Dynamically imports a module from the given file path and retrieves a callable for a specified function
    with its parameters pre-applied.

    Args:
        file_path (str): The full path to the Python file.
        function_name (str): The name of the function to retrieve.
        parameters (dict): The parameters to pass to the function.

    Returns:
        A callable object that, when executed, runs the function with the given parameters.
    """
    try:
        # Ensure the file exists
        if not os.path.isfile(file_path):
            raise ImportError(f"File not found: {file_path}")

        # Extract module name from the file name
        module_name = os.path.splitext(os.path.basename(file_path))[0]

        # Dynamically load the module
        module_spec = importlib.util.spec_from_file_location(module_name, file_path)
        module = importlib.util.module_from_spec(module_spec)
        module_spec.loader.exec_module(module)

        # Ensure the function exists in the module
        if not hasattr(module, function_name):
            raise ImportError(f"Function '{function_name}' not found in module {module_name}")

        # Retrieve the function object
        func = getattr(module, function_name)

        # Return a callable that delays execution
        def delayed_execution():
            return func(**parameters)

        return delayed_execution

    except (ImportError, AttributeError, ValueError, FileNotFoundError, TypeError) as e:
        raise ImportError(f"Failed to retrieve function '{function_name}' from {file_path}: {e}")

class StateButtonGrid(Static):
    def __init__(self, state_machine: StateMachine, *args, state_machine_active_on_mount=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.state_machine = state_machine
        self.all_actions = self.get_ordered_actions()
        self.state_machine_active_on_mount = state_machine_active_on_mount

    def get_ordered_actions(self) -> List[str]:
        all_actions = set()
        for state in self.state_machine.states.values():
            if isinstance(state, UIState):
                all_actions.update(state.get_visible_transitions())  # Only include visible transitions
            else:
                all_actions.update(state.transitions.keys())  # Fallback in case of base State

        ordered_actions = []
        visited_states = set()
        state_queue = [self.state_machine.current_state]

        while state_queue:
            current_state = state_queue.pop(0)
            if current_state.name in visited_states:
                continue
            visited_states.add(current_state.name)

            if isinstance(current_state, UIState):
                state_actions = list(current_state.get_visible_transitions())  # Only consider visible actions
            else:
                state_actions = list(current_state.transitions.keys())  # Fallback in case of base State

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
        """Disable or update buttons based on state_machine_active_on_mount flag."""
        self.disable_buttons_initially()

    def disable_buttons_initially(self) -> None:
        """Disable all buttons initially unless the state machine is active."""
        if not self.state_machine_active_on_mount:
            for button in self.query("Button"):
                button.disabled = True
        else:
            self.update_buttons() 

    def __bck__on_button_pressed(self, event: Button.Pressed) -> None:
        action = str(event.button.label)
        self.post_message(ActionSelected(action))
    

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """
        Handle button pressed events. Executes associated function if defined in the current state.

        Args:
            event (Button.Pressed): The button press event.
        """
        action = str(event.button.label)

        # Post the action message to notify other parts of the system
        self.post_message(ActionSelected(action))

        # Check if the current state has a function to execute
        current_state = self.state_machine.current_state
        
        if current_state.function_spec:
            try:
                # Import the module dynamically
                function_name = next(iter(current_state.function_spec.keys()))
                function_location = current_state.function_spec[function_name]['location']
                function_params = current_state.function_spec[function_name]['parameters']

                # Dynamically import and retrieve the callable
                func_callable = dynamic_import(function_location, function_name, function_params)

                if not func_callable:
                    raise ImportError(f"Failed to retrieve callable for function '{function_name}' from '{function_location}'")

                # Execute the callable
                result = func_callable()  # Executes the function with pre-applied parameters

                # Notify success
                self.app.notify(f"Result '{result}' successfully executed.", severity="info")

            except Exception as e:
                # Notify failure
                self.app.notify(f"Error executing action '{action}': {str(e)}", severity="error")
        else:
            # Notify no function found
            self.app.notify(f"No action defined for '{action}' in the current state.", severity="warning")


        
    def update_buttons(self) -> None:
        """Update the buttons based on allowed actions from the state machine."""
        allowed_actions = self.state_machine.get_available_commands()
        for button in self.query("Button"):
            action = str(button.label)
            button.disabled = action not in allowed_actions

    @on(SessionStateChanged)
    def on_session_state_changed(self, event: SessionStateChanged) -> None:
        """Enable or disable all buttons based on session state."""
        if event.session_active:
            # Enable buttons based on state machine logic
            self.update_buttons()
        else:
            # No active session, disable all buttons
            for button in self.query("Button"):
                button.disabled = True
