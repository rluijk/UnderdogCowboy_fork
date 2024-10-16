import logging
import asyncio
from textual import on
from textual.app import App, ComposeResult
from textual.widgets import Header, Select, Input, Static

# Mockup categories that can be refreshed
MOCK_CATEGORIES = ["Category 1", "Category 2", "Category 3", "Category 4", "Category 5"]

# Configure the logging to log to a file 'selecttry_01.log'
logging.basicConfig(
    filename='selecttry_01.log', 
    level=logging.DEBUG, 
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Define the LoadingIndicator as a simple Static widget for now
class LoadingIndicator(Static):
    pass

class SelectApp(App):
    CSS = """
    Screen {
        align: center top;  /* Align content to the top of the screen */
    }

    Select {
        width: 60;
        margin: 2;
    }

    Input {
        width: 60;
        margin: 2;
    }

    #loading-indicator {
        margin-top: 1;
        visibility: hidden;  /* Hidden by default but takes up space */
    }

    #loading-indicator.visible {
        visibility: visible;  /* Make the indicator visible without affecting layout */
    }
    """

    def __init__(self):
        super().__init__()
        # Initially, the Select widget only has the "Create Initial Categories" option
        self.categories = [("create_initial", "Create Initial Categories")]
        self.selected_category = None
        logging.debug("Initialized with Create Initial Categories")

    def compose(self) -> ComposeResult:
        yield Header()
        self.select = Select(self.categories)  # Initial Select widget
        yield self.select
        # Add the LoadingIndicator, hidden by default
        self.loading_indicator = LoadingIndicator("     Loading...", id="loading-indicator")
        yield self.loading_indicator
        self.input_box = Input(placeholder="Rename selected category")
        self.input_box.visible = False  # Hidden initially
        yield self.input_box

    async def show_loading_indicator(self):
        """Show the loading indicator without affecting layout."""
        self.loading_indicator.add_class("visible")
        self.refresh()

    async def hide_loading_indicator(self):
        """Hide the loading indicator without affecting layout."""
        self.loading_indicator.remove_class("visible")
        self.refresh()

    @on(Select.Changed)
    async def select_changed(self, event: Select.Changed) -> None:
        selected_value = event.value
        logging.info(f"Select changed: {selected_value}")

        # Handle when no selection has been made (BLANK state)
        if selected_value == Select.BLANK:
            logging.info("No selection made (BLANK)")
            return

        # Handle when the user selects "Create Initial Categories"
        if selected_value == "Create Initial Categories":
            # Show "Waiting" and start async retrieval of mock categories
            self.select.set_options([("waiting", "Waiting for categories...")])
            await self.show_loading_indicator()  # Show the loading indicator
            await asyncio.sleep(5)  # Simulate the 5-second delay for async retrieval
            logging.info("Categories retrieved.")
            
            # Populate with mock categories after waiting
            self.categories = [("refresh_all", "Refresh All")] + [
                (category, category) for category in MOCK_CATEGORIES
            ]
            self.select.set_options(self.categories)  # Update the Select widget with new categories
            self.select.value = MOCK_CATEGORIES[0]  # Automatically select the first category
            logging.debug(f"Automatically selected first category: {MOCK_CATEGORIES[0]}")
            await self.hide_loading_indicator()  # Hide the loading indicator after retrieval
        elif selected_value == "Refresh All":
            # Fetch some new mock categories (this can be replaced with a real storage fetch)
            new_categories = ["Category 6", "Category 7", "Category 8", "Category 9", "Category 10"]
            self.categories = [("refresh_all", "Refresh All")] + [
                (category, category) for category in new_categories
            ]
            self.select.set_options(self.categories)  # Update the Select widget again
            logging.debug("Categories refreshed with new mock categories")
        else:
            # A category has been selected, show the input box for renaming
            self.selected_category = selected_value
            if selected_value != Select.BLANK:  # Make sure selected value isn't BLANK
                self.input_box.value = selected_value
            self.input_box.visible = True
            logging.info(f"Category selected for renaming: {selected_value}")
        
        self.refresh()

    @on(Input.Submitted)
    def input_submitted(self, event: Input.Submitted) -> None:
        # Handle renaming of the selected category
        if self.selected_category:
            # Update the selected category name
            new_name = event.value
            logging.info(f"Renaming category {self.selected_category} to {new_name}")
            for i, (key, label) in enumerate(self.categories):
                if label == self.selected_category:  # Compare with the display value
                    self.categories[i] = (new_name, new_name)
                    break
            self.select.set_options(self.categories)  # Update the Select widget with the new names
            self.input_box.visible = False
            self.selected_category = None
            self.refresh()
            logging.debug(f"Category renamed to {new_name}")


if __name__ == "__main__":
    app = SelectApp()
    app.run()
