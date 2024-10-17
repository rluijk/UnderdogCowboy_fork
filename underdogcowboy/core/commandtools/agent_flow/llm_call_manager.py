
import asyncio
from typing import Any, Callable, Optional
import logging


from concurrent.futures import ThreadPoolExecutor

from events.message_mixin import MessageEmitterMixin
from events.llm_events import LLMCallComplete, LLMCallError

from exceptions import MessagePostTargetNotSetError

class LLMCallManager(MessageEmitterMixin):
    """Manages asynchronous LLM (Large Language Model) calls with a task queue and thread pool executor."""

    def __init__(self, max_workers=5):
        super().__init__()  
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self._task_queue = asyncio.Queue()
        asyncio.create_task(self._process_queue())

    async def _process_queue(self):
        while True:
            task = await self._task_queue.get()
            asyncio.create_task(self._handle_task(*task))
            self._task_queue.task_done()        

    async def _handle_task(self, llm_function, *args):
        input_id = args[-1]  # Assume input_id is always the last argument
        try:
            result = await asyncio.to_thread(llm_function, *args[:-1])
            # Check if result is a tuple and unpack
            if isinstance(result, tuple):
                response, adm = result
            else:
                response = result
                adm = None
            self.post_message(LLMCallComplete(sender=self, input_id=input_id, result=response, adm=adm))
        except Exception as e:
            self.post_message(LLMCallError(sender=self, input_id=input_id, error=str(e)))


    async def submit_llm_call(self, llm_function, llm_config, processor, input_id, message_text):
        """Submits an LLM call to the task queue."""
        logging.info(f"Submitting LLM call for input_id: {input_id}")
        if not self._message_post_target:
            raise MessagePostTargetNotSetError("Message post target not set.")
        
        # Put the task in the async queue for processing
        await self._task_queue.put((
            llm_function,
            llm_config,
            processor,
            message_text,
            input_id  # Ensure input_id is last
        ))
        logging.info(f"LLM call for input_id {input_id} has been queued")

    async def submit_analysis_call(self, llm_function, llm_config, agent_name, input_id, pre_prompt=None, post_prompt=None, adm=None):
        """Submits an analysis LLM call to the task queue using the provided analysis_function."""
        logging.info(f"Submitting analysis call for input_id: {input_id}")
        if not self._message_post_target:
            raise MessagePostTargetNotSetError("Message post target not set.")

        # Put the task in the async queue for processing
        await self._task_queue.put((
            llm_function,
            llm_config,
            agent_name,
            pre_prompt,
            post_prompt,
            adm,
            input_id  # Ensure input_id is the last argument
        ))

        logging.info(f"Analysis call for input_id {input_id} has been queued")
