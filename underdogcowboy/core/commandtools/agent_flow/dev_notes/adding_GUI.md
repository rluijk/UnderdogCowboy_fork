# Introduction

This guide is divided into two parts to help you add new buttons and corresponding GUI elements to the system. 

- **Part 1** is a straightforward step-by-step instruction to quickly implement a new button and get things done.
- **Part 2** dives deeper into the technical details, providing a more in-depth explanation of how the abstractions in the system work behind the scenes. 

Whether you’re looking for quick implementation or a deeper understanding, this guide has you covered.


# Steps to Add a New Button and GUI Part:

1. **Create the UI Component**:
   - Define a new class for the UI element that will be loaded dynamically when the button is pressed.
   - Example for a "Save" button:
     ```python
     class SaveUI(Static):
         def compose(self) -> ComposeResult:
             yield Button("Confirm Save", id="confirm-save-button")

         def on_button_pressed(self, event: Button.Pressed) -> None:
             if event.button.id == "confirm-save-button":
                 self.parent.post_message(LeftSideButtonPressed("confirm-save"))
     ```

2. **Create the State Transition Function**:
   - Define a new function that will handle the state transition or any action when the new UI is confirmed.
   - Example:
     ```python
     def transition_to_save_state(self) -> None:
         save_state = self.state_machine.states.get("save_ready")
         if save_state:
             self.state_machine.current_state = save_state
             self.query_one(StateInfo).update_state_info(self.state_machine, "")
             self.query_one(StateButtonGrid).update_buttons()
     ```

3. **Map the Button to the UI and Action**:
   - Modify the `get_ui_and_action` function to map the new button ID (e.g., `"save-button"`) to the new UI class (`SaveUI`) and action function (`transition_to_save_state`).
   - Example:
     ```python
     def get_ui_and_action(self, button_id: str):
         if button_id == "save-button":
             ui_class_name = "SaveUI"
             action_func_name = "transition_to_save_state"
         # Add more button mappings here...
     ```

4. **Add the Button in the Interface**:
   - Add the button in the `LeftSideButtons` class, so it appears in the UI.
   - Example:
     ```python
     yield Button("Save", id="save-button", classes="left-side-button")
     ```

5. **Test the Button**:
   - Run the app and verify that clicking the new button correctly loads the new UI and triggers the state transition or action on confirmation.

---

# Technnical Explanation

Here’s a **technical note** using the `save-button` example, explaining how this works with the generic abstraction in the current system:

---

### Save Button: Technical Breakdown of the Generic Code

#### 1. **UI Component: `SaveUI`**
   The UI for the "Save" functionality is represented by a class (`SaveUI`) that is dynamically loaded into the container when the button is pressed. This is abstracted into a `Static` widget:

   ```python
   class SaveUI(Static):
       def compose(self) -> ComposeResult:
           yield Button("Confirm Save", id="confirm-save-button")

       def on_button_pressed(self, event: Button.Pressed) -> None:
           if event.button.id == "confirm-save-button":
               self.parent.post_message(LeftSideButtonPressed("confirm-save"))
   ```

   **Key Concepts**:
   - **Dynamic Loading**: The `SaveUI` widget is not instantiated at the start. Instead, it’s dynamically created and mounted to the container when the "Save" button is clicked.
   - **Event Handling**: The `on_button_pressed` method captures the button click and posts a message (e.g., `"confirm-save"`) back to the application to handle the logic.

#### 2. **State Transition Function: `transition_to_save_state`**
   The state transition is handled by the `transition_to_save_state` function, which ensures the application moves to the correct state after the "Confirm Save" button is clicked.

   ```python
   def transition_to_save_state(self) -> None:
       save_state = self.state_machine.states.get("save_ready")
       if save_state:
           self.state_machine.current_state = save_state
           self.query_one(StateInfo).update_state_info(self.state_machine, "")
           self.query_one(StateButtonGrid).update_buttons()
       else:
           logging.error("Save state not found")
   ```

   **Key Concepts**:
   - **State Handling**: The function interacts with the `StateMachine` to move the application to the `save_ready` state.
   - **UI Update**: Once the state transition is complete, the `StateInfo` and `StateButtonGrid` are updated to reflect the new state.

#### 3. **Mapping: `get_ui_and_action`**
   The `get_ui_and_action` method is responsible for dynamically resolving the appropriate UI component (`SaveUI`) and the corresponding action function (`transition_to_save_state`) based on the button ID.

   ```python
   def get_ui_and_action(self, button_id: str):
       if button_id == "save-button":
           ui_class_name = "SaveUI"
           action_func_name = "transition_to_save_state"
       # Additional button mappings here...
   ```

   **Key Concepts**:
   - **Dynamic Resolution**: The button ID (`"save-button"`) is mapped to the corresponding UI class and function. This abstraction allows for easy extension without needing hardcoded behavior.
   - **Scalability**: This approach allows you to easily add new buttons by mapping their IDs to UI components and state transition functions.

#### 4. **Rendering the Button in the UI: `LeftSideButtons`**
   The `save-button` is added to the sidebar by rendering it through the `LeftSideButtons` container. This ensures that the button appears in the UI.

   ```python
   class LeftSideButtons(Container):
       def compose(self) -> ComposeResult:
           yield Button("Save", id="save-button", classes="left-side-button")
   ```

   **Key Concepts**:
   - **Modular UI**: The button is part of the modular UI that is created on the left side. Each button is added dynamically, making the system flexible.

#### 5. **Generic Button Handling: `on_left_side_button_pressed`**
   When the "Save" button is clicked, the generic `on_left_side_button_pressed` function calls `ui_factory`, which dynamically loads the correct UI (e.g., `SaveUI`) and executes the corresponding action when confirmed.

   ```python
   def on_left_side_button_pressed(self, event: LeftSideButtonPressed) -> None:
       dynamic_container = self.query_one(DynamicContainer)
       dynamic_container.clear_content()

       try:
           # Use the UI factory to get the corresponding UI and action
           ui_class, action = self.ui_factory(event.button_id)
           dynamic_container.load_content(ui_class)
       except ValueError as e:
           logging.error(f"Error: {e}")
   ```

   **Key Concepts**:
   - **UI Factory**: The `ui_factory` method resolves the correct UI component (`SaveUI`) and action (`transition_to_save_state`) based on the button ID.
   - **Event-Driven**: The system is driven by events, where button clicks trigger the appropriate actions and dynamically load the corresponding UI.

---

### Summary:
- **Dynamic and Scalable**: The system dynamically loads the correct UI (`SaveUI`) and triggers the correct action (`transition_to_save_state`) based on button clicks.
- **Separation of Concerns**: Each part of the system (UI, state management, button handling) is modular, making it easy to extend without disrupting other parts.
- **Abstraction Layer**: The `get_ui_and_action` method provides an abstraction layer that allows for flexible button mappings, reducing the need for hardcoded logic.

By following this pattern, you can implement new buttons and their corresponding actions while leveraging the power of the abstractions in place.