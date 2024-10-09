

from typing import Any, Callable, Optional
import logging

import asyncio
from concurrent.futures import ThreadPoolExecutor

from events.message_mixin import MessageEmitterMixin
from events.llm_events import LLMCallComplete, LLMCallError


class MessagePostTargetNotSetError(Exception):
    """Exception raised when message post target is not set."""
    pass


class LLMCallManager(MessageEmitterMixin):
    """Manages asynchronous LLM (Large Language Model) calls with a task queue and thread pool executor."""

    def __init__(self, max_workers=5):
        super().__init__()  
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self._task_queue = asyncio.Queue()
        asyncio.create_task(self._process_queue())

    async def _process_queue(self):
        """Continuously processes tasks from the queue."""
        while True:
            llm_function, input_value, pre_prompt, post_prompt, input_id = await self._task_queue.get()
            # Submit the task to the thread pool and handle completion with a callback
            asyncio.create_task(self._handle_task(llm_function, input_value, pre_prompt, post_prompt, input_id))
            self._task_queue.task_done()

    async def _handle_task(self, llm_function, input_value, pre_prompt, post_prompt, input_id):
        """Handles individual LLM call tasks."""
        loop = asyncio.get_event_loop()
        try:
            # Run the LLM call in the background using a thread pool
            result = await loop.run_in_executor(
                self.executor, 
                llm_function, input_value, pre_prompt, post_prompt
            )
            logging.info(f"LLMCallManager -> handled llm task, sending LLMCallComplete event {result}")
            # Post a completion message to the event system when done
            self.post_message(LLMCallComplete(input_id=input_id, result=result))
        except Exception as e:
            # If any error occurs, post an error message to the event system
            self.post_message(LLMCallError(input_id=input_id, error=str(e)))

    async def submit_llm_call(self, llm_function, input_value, input_id, pre_prompt=None, post_prompt=None):
        """Submits an LLM call to the task queue."""
        logging.info(f"Submitting LLM call for input_id: {input_id}")
        if not self._message_post_target:
            raise MessagePostTargetNotSetError("Message post target not set.")
        
        # Put the task in the async queue for processing
        await self._task_queue.put((llm_function, input_value, pre_prompt, post_prompt, input_id))
        logging.info(f"LLM call for input_id {input_id} has been queued")

    async def submit_analysis_call(self, llm_function, llm_config, agent_name, input_id, pre_prompt=None, post_prompt=None):
        """Submits an analysis LLM call to the task queue using the provided analysis_function."""
        logging.info(f"Submitting analysis call for input_id: {input_id}")
        if not self._message_post_target:
            raise MessagePostTargetNotSetError("Message post target not set.")
        
        # Pass the analysis_function as the llm_function argument
        await self._task_queue.put((
            llm_function,       # Pass the provided analysis function as the llm_function
            llm_config,         # Input value (llm_config)
            agent_name,         # Input value (agent_name)
            pre_prompt,         # Pre prompt argument
            post_prompt,        # Post prompt argument
            input_id            # Task identifier
        ))
        logging.info(f"Analysis call for input_id {input_id} has been queued")
