import asyncio
import pyperclip

from textual import on

# imports for connecting to Textual event driven system 
from events.message_mixin import MessageEmitterMixin
from events.copy_paste_events import LLMResultReceived, CopyToClipboard, CopySpecificContent
from exceptions import MessagePostTargetNotSetError

class ClipBoardCopy(MessageEmitterMixin):
    
    def __init__(self):
        super().__init__()  # Initialize the mixin
        self.latest_result = None  # Instance variable to store the result
        
    @on(LLMResultReceived)
    async def handle_llm_result_received(self, event: LLMResultReceived):
        self.latest_result = event.result
        await asyncio.get_event_loop().run_in_executor(None, self.copy_to_clipboard, self.latest_result)
    
    @on(CopyToClipboard)
    async def handle_copy_to_clipboard(self, event: CopyToClipboard):
        if self.latest_result:
            await self.copy_to_clipboard(self.latest_result)
        else:
            self.app.notify("No result available to copy.", severity="warning")

    @on(CopySpecificContent)
    async def handle_copy_specific_content(self, event: CopySpecificContent):
        await self.copy_to_clipboard(event.content)

    async def copy_to_clipboard(self, content: str):
        try:
            pyperclip.copy(content)
            self.app.notify("Content copied to clipboard!", severity="info")
        except pyperclip.PyperclipException as e:
            self.app.notify(f"Failed to copy content: {e}", severity="error")


