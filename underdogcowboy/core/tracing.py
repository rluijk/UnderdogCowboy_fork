import os
import requests
from uuid import uuid4

from abc import ABC, abstractmethod
from contextlib import contextmanager
from typing import Optional, Any, Dict

from datetime import datetime

import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


class TracerInterface(ABC):
    @abstractmethod
    @contextmanager
    def trace(self, name: str):
        pass

    @abstractmethod
    @contextmanager
    def span(self, name: str):
        pass

    @abstractmethod
    def log(self, name: str, content: Any):
        pass

    @abstractmethod
    def log_metric(self, name: str, value: float):
        pass

class NoOpTracer(TracerInterface):
    @contextmanager
    def trace(self, name: str):
        yield self

    @contextmanager
    def span(self, name: str):
        yield self

    def log(self, name: str, content: Any):
        pass

    def log_metric(self, name: str, value: float):
        pass

class LangSmithTracer:
    def __init__(self, api_key: Optional[str] = None):
        if api_key:
            os.environ['LANGCHAIN_API_KEY'] = api_key 
        elif 'LANGCHAIN_API_KEY' not in os.environ:
            raise ValueError("LangSmith API key is required. Set it in the environment or pass it to the constructor.")
        
        self.headers = {"x-api-key": os.environ['LANGCHAIN_API_KEY']}
        self.base_url = "https://api.smith.langchain.com"
        self.current_run = None
        self.run_stack = []
        self.run_data: Dict[str, Dict] = {}

    def post_run(self, name: str, run_type: str, inputs: dict, parent_id: Optional[str] = None) -> str:
        run_id = uuid4().hex
        data = {
            "id": run_id,
            "name": name,
            "run_type": run_type,
            "inputs": inputs,
            "start_time": datetime.utcnow().isoformat(),
        }
        if parent_id:
            data["parent_run_id"] = parent_id
        
        response = requests.post(
            f"{self.base_url}/runs",
            json=data,
            headers=self.headers
        )
        response.raise_for_status()
        self.run_data[run_id] = {"outputs": {}, "end_time": None}
        return run_id

    def patch_run(self, run_id: str, end: bool = False):
        if run_id not in self.run_data:
            logger.warning(f"Attempted to patch non-existent run: {run_id}")
            return

        data = self.run_data[run_id]
        patch_data = {}

        if data["outputs"]:
            patch_data["outputs"] = data["outputs"]
            data["outputs"] = {}  # Clear outputs after sending

        if end:
            patch_data["end_time"] = datetime.utcnow().isoformat()

        if not patch_data:
            return  # No data to patch

        try:
            response = requests.patch(
                f"{self.base_url}/runs/{run_id}",
                json=patch_data,
                headers=self.headers
            )
            response.raise_for_status()
            if end:
                del self.run_data[run_id]  # Remove run data after ending
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 409:
                logger.warning(f"Run {run_id} has already ended. Skipping update.")
                del self.run_data[run_id]  # Remove run data if it's already ended
            else:
                raise

    @contextmanager
    def trace(self, name: str):
        try:
            logger.debug(f"Creating trace: {name}")
            run_id = self.post_run(name=name, run_type="chain", inputs={})
            self.run_stack.append(run_id)
            self.current_run = run_id
            logger.debug(f"Created trace: {name}, run ID: {run_id}")
            yield self
        except Exception as e:
            logger.error(f"Error in trace {name}: {str(e)}")
            raise
        finally:
            if self.run_stack:
                run_id = self.run_stack.pop()
                self.patch_run(run_id, end=True)
            self.current_run = self.run_stack[-1] if self.run_stack else None

    @contextmanager
    def span(self, name: str):
        if not self.current_run:
            raise ValueError("No active trace. Spans must be created within a trace.")
        try:
            run_id = self.post_run(name=name, run_type="tool", inputs={}, parent_id=self.current_run)
            self.run_stack.append(run_id)
            self.current_run = run_id
            yield self
        except Exception as e:
            logger.error(f"Error in span {name}: {str(e)}")
            raise
        finally:
            if self.run_stack:
                run_id = self.run_stack.pop()
                self.patch_run(run_id, end=True)
            self.current_run = self.run_stack[-1] if self.run_stack else None

    def log(self, name: str, content: Any):
        if self.current_run:
            self.run_data[self.current_run]["outputs"][name] = content
            # Don't patch immediately, wait for more logs or end of run

    def log_metric(self, name: str, value: float):
        if self.current_run:
            self.run_data[self.current_run]["outputs"][name] = value
            # Don't patch immediately, wait for more logs or end of run

    def flush(self):
        """Manually flush all pending updates."""
        for run_id in list(self.run_data.keys()):
            self.patch_run(run_id)

class TracingProxy:
    def __init__(self, use_langsmith: bool = False, api_key: Optional[str] = None):
        if use_langsmith and api_key:
            self.tracer: TracerInterface = LangSmithTracer(api_key)
        else:
            self.tracer: TracerInterface = NoOpTracer()

    def set_tracer(self, use_langsmith: bool):
        self.tracer = LangSmithTracer() if use_langsmith else NoOpTracer()

    @contextmanager
    def trace(self, name: str):
        with self.tracer.trace(name) as trace:
            yield trace

    @contextmanager
    def span(self, name: str):
        with self.tracer.span(name) as span:
            yield span

    def log(self, name: str, content: Any):
        self.tracer.log(name, content)

    def log_metric(self, name: str, value: float):
        self.tracer.log_metric(name, value)