import logging
from textual.message import Message

class MessageEmitterMixin:
    def __init__(self):
        self._message_post_target = None

    def set_message_post_target(self, post_target):
        """Set the target widget that will handle message posting."""
        self._message_post_target = post_target
        logging.info(f"post target message set to: {self._message_post_target}")

    def post_message(self, message: Message):
        """Post a message if a target is set."""
        if self._message_post_target:
            self._message_post_target.post_message(message)
        else:
            raise ValueError("Message post target is not set.")
