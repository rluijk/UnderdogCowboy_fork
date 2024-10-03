import logging
import asyncio
from concurrent.futures import ThreadPoolExecutor
import os
import json
from textual.app import App, ComposeResult
from textual.widgets import Static, Button, LoadingIndicator
from textual.containers import Vertical
from textual.message import Message
from underdogcowboy import AgentDialogManager, agentclarity
from underdogcowboy.core.config_manager import LLMConfigManager

# Clear existing handlers and set up logging to a file
for handler in logging.root.handlers[:]:
    logging.root.removeHandler(handler)

logging.basicConfig(
    filename='app_test_async_03.log', 
    level=logging.DEBUG, 
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def run_analysis(llm_config, agent_name):
    try:
        logging.info("Starting analysis with agent '%s' and config: %s", agent_name, llm_config)
        model_id = llm_config['model_id']
        adm = AgentDialogManager([agentclarity], model_name=model_id)
        
        agents_dir = os.path.expanduser("~/.underdogcowboy/agents")
        agent_file = os.path.join(agents_dir, f"{agent_name}.json")
        
        if not os.path.exists(agent_file):
            logging.error("Agent file for '%s' not found.", agent_name)
            return f"Error: Agent file for '{agent_name}' not found."

        with open(agent_file, 'r') as f:
            agent_data = json.load(f)

        response = agentclarity >> f"Analyze this agent definition: {json.dumps(agent_data)}"
        logging.info("Analysis completed successfully.")
        return response.text
    except Exception as e:
        logging.error("Error during analysis: %s", str(e))
        return f"Error: {str(e)}"

class AnalysisComplete(Message):
    def __init__(self, result: str):
        self.result = result
        super().__init__()

class AnalysisError(Message):
    def __init__(self, error: str):
        self.error = error
        super().__init__()

class AnalyzeUI(Static):
    """A UI for displaying and running analysis on an agent definition"""
    
    def compose(self) -> ComposeResult:
        yield Static("Analysis Result:", id="result-label", classes="result-label hidden")
        yield Static(id="analysis-result", classes="hidden result-compose")
        yield Button("Start Analysis", id="start-analysis-button", classes="hidden")
        yield Button("Re-run Analysis", id="rerun-analysis-button", classes="hidden")
        yield LoadingIndicator(id="loading-indicator", classes="hidden")

    def on_mount(self) -> None:
        self.executor = ThreadPoolExecutor(max_workers=1)
        self.check_existing_analysis()

    def on_unmount(self) -> None:
        self.executor.shutdown(wait=False)

    def check_existing_analysis(self) -> None:
        existing_analysis = self.app.storage_manager.get_data("last_analysis")
        if existing_analysis:
            self.show_result(existing_analysis)
            self.query_one("#rerun-analysis-button").remove_class("hidden")
        else:
            self.query_one("#start-analysis-button").remove_class("hidden")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id in ["start-analysis-button", "rerun-analysis-button"]:
            self.run_analysis()

    def run_analysis(self) -> None:
        self.query_one("#start-analysis-button").add_class("hidden")
        self.query_one("#rerun-analysis-button").add_class("hidden")
        self.query_one("#analysis-result").add_class("hidden")
        self.query_one("#loading-indicator").remove_class("hidden")

        asyncio.create_task(self.perform_analysis())

    async def perform_analysis(self) -> None:
        try:
            logging.info("Analysis started")
            
            llm_config = self.app.get_current_llm_config()
            if not llm_config:
                raise ValueError("No LLM configuration available.")

            current_agent = self.app.agent_name_plain
            if not current_agent:
                raise ValueError("No agent currently loaded. Please load an agent first.")

            result = await asyncio.get_event_loop().run_in_executor(
                self.executor, run_analysis, llm_config, current_agent
            )

            if result.startswith("Error:"):
                raise ValueError(result)

            logging.info("Analysis completed")
            self.post_message(AnalysisComplete(result))
        except Exception as e:
            logging.error(f"Analysis error: {str(e)}")
            self.post_message(AnalysisError(str(e)))

    def on_analysis_complete(self, message: AnalysisComplete) -> None:
        self.update_and_show_result(message.result)
        self.query_one("#loading-indicator").add_class("hidden")

    def on_analysis_error(self, message: AnalysisError) -> None:
        self.show_error(message.error)
        self.query_one("#loading-indicator").add_class("hidden")

    def update_and_show_result(self, result: str) -> None:
        self.app.storage_manager.update_data("last_analysis", result)
        self.show_result(result)

    def show_result(self, result: str) -> None:
        self.query_one("#result-label").remove_class("hidden")
        result_widget = self.query_one("#analysis-result")
        result_widget.update(result)
        result_widget.remove_class("hidden")
        self.query_one("#rerun-analysis-button").remove_class("hidden")

    def show_error(self, error_message: str) -> None:
        self.query_one("#start-analysis-button").remove_class("hidden")
        self.app.notify(f"Error: {error_message}", severity="error")

class TestApp(App):
    DEFAULT_PROVIDER = 'anthropic'
    DEFAULT_MODEL_ID = 'claude-3-5-sonnet-20240620'
    DEFAULT_MODEL_NAME = 'Claude 3.5 Sonnet'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.llm_config_manager = LLMConfigManager()
        self.set_default_llm()
        self.agent_name_plain = "mermaid"
        self.storage_manager = self  # Mock storage manager

    def compose(self) -> ComposeResult:
        yield AnalyzeUI()

    def set_default_llm(self):
        logging.info("Setting default LLM configuration.")
        available_models = self.llm_config_manager.get_available_models()
        if f"{self.DEFAULT_PROVIDER}:{self.DEFAULT_MODEL_ID}" in available_models:
            self.llm_config_manager.update_model_property(self.DEFAULT_PROVIDER, 'selected_model', self.DEFAULT_MODEL_ID)
        else:
            logging.warning("Default model not found. Prompting configuration.")
            self.configure_default_llm()

    def configure_default_llm(self):
        try:
            logging.info("Configuring default LLM.")
            self.llm_config_manager.get_credentials(self.DEFAULT_PROVIDER)
            self.llm_config_manager.update_model_property(self.DEFAULT_PROVIDER, 'selected_model', self.DEFAULT_MODEL_ID)
        except Exception as e:
            logging.error("Failed to configure default LLM: %s", str(e))
            self.notify("Failed to configure default LLM. Please check your settings.", severity="error")

    def get_current_llm_config(self):
        try:
            return self.llm_config_manager.get_credentials(self.DEFAULT_PROVIDER)
        except Exception as e:
            logging.error("Failed to retrieve LLM configuration: %s", str(e))
            return None

    def get_data(self, key):
        # Mock implementation for storage manager
        return None

    def update_data(self, key, value):
        # Mock implementation for storage manager
        pass

    def notify(self, message, severity="information"):
        logging.info(f"Notification: {message} (Severity: {severity})")

if __name__ == "__main__":
    app = TestApp()
    logging.info("Starting TestApp.")
    app.run()