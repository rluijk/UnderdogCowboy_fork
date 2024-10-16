import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from events.message_mixin import MessageEmitterMixin
from events.llm_events import LLMCallComplete, LLMCallError
from collections import namedtuple

"""
For potential improvement ideas:
underdogcowboy/core/commandtools/agent_flow/dev_notes/llm_manager_notes.md
"""

class MessagePostTargetNotSetError(Exception):
    """Exception raised when message post target is not set."""
    pass


class LLMCallManager(MessageEmitterMixin):
    """Manages asynchronous LLM calls with a task queue and thread pool executor."""

    def __init__(self, max_workers=5):
        super().__init__()
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self._task_queue = asyncio.Queue()
        self._shutdown = False
        try:
            asyncio.create_task(self._process_queue())
        except Exception as e:
            logging.exception("Failed to create background task for processing the queue: {e}")

    async def _process_queue(self):
        while not self._shutdown:
            task = await self._task_queue.get()
            if task is None:
                break
            logging.debug(f"Processing task: {task}")
            asyncio.create_task(self._handle_task(task))
            self._task_queue.task_done()

    async def _handle_task(self, task):
        loop = asyncio.get_running_loop()
        input_id = task.input_id
        logging.debug(f"Handling task for input_id: {input_id} with args: {task.args}")
        try:
            result = await loop.run_in_executor(
                self.executor,
                task.llm_function,
                *task.args  # Pass all other args to llm_function
            )
            logging.info(f"LLM call for input_id {input_id} completed successfully with result: {result}")
            self.post_message(LLMCallComplete(input_id=input_id, result=result, metadata={
                'pre_prompt': task.pre_prompt,
                'post_prompt': task.post_prompt,
                'args': task.args
            }))
        except Exception as e:
            logging.exception(f"LLM call for input_id {input_id} failed with error: {e}")
            self.post_message(LLMCallError(input_id=input_id, error=str(e)))

    async def submit_llm_call(self, llm_function, *args, input_id, pre_prompt=None, post_prompt=None):
        """
        Submit an LLM call to be processed asynchronously.

        This method adds an LLM call task to the internal queue, which will be executed in the background using a 
        thread pool executor. The task will process the given LLM function along with any provided arguments, and 
        will generate appropriate events upon success or failure of the LLM call.

        Args:
            llm_function (Callable): The function representing the LLM call to be executed.
            *args: Positional arguments to be passed to the LLM function.
            input_id (Any): A unique identifier for the input, used for tracking the task.
            pre_prompt (Optional[str]): An optional pre-prompt to be passed to the LLM function.
            post_prompt (Optional[str]): An optional post-prompt to be passed to the LLM function.

        Raises:
            MessagePostTargetNotSetError: If the message post target is not set before submission.
                Ensure that the `set_message_post_target(target)` method is called before submitting any LLM calls.
                The message post target is typically set to an object that can handle messages such as LLMCallComplete
                or LLMCallError events, which are posted by this manager after processing tasks.
        """
        logging.info(f"Submitting LLM call for input_id: {input_id}")
        if not self._message_post_target:
            logging.error("Message post target not set for input_id: {input_id}")
            raise MessagePostTargetNotSetError("Message post target not set. Please use `set_message_post_target(target)` to set a valid message post target before submitting LLM calls.")

        # Define a named tuple for the task
        LLMTask = namedtuple('LLMTask', ['llm_function', 'args', 'pre_prompt', 'post_prompt', 'input_id'])
        
        # Prepare the task with all arguments
        task = LLMTask(llm_function=llm_function, args=args, pre_prompt=pre_prompt, post_prompt=post_prompt, input_id=input_id)
        logging.debug(f"Task prepared for input_id {input_id}: {task}")

        # Put the task in the async queue for processing
        await self._task_queue.put(task)
        logging.info(f"LLM call for input_id {input_id} has been queued")

    async def shutdown(self):
        """Gracefully shuts down the task processing loop."""
        logging.info("Shutting down LLMCallManager...")
        self._shutdown = True
        await self._task_queue.put(None)
        await self._task_queue.join()
        self.executor.shutdown(wait=True)
        logging.info("LLMCallManager has been shut down.")