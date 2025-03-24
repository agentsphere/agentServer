

import logging
logger = logging.getLogger(__name__)


import asyncio
from pydantic import BaseModel


stream_queues = {}


async def add_to_queue(chat_id: str, msg: str):
    logger.info(f"Adding to queue: {msg} for chat_id: {chat_id}")
    logger.info(f"Current queues: {stream_queues}")
    # Push result to the appropriate queue
    if chat_id in stream_queues:
        await stream_queues[chat_id].put(f"Step: {msg}")

    return True


def add_queue_for_chat(chat_id: str, queue: asyncio.Queue = None):
    logger.info(f"Adding queue for chat_id: {chat_id} with queue: {queue}")
    if queue is None:
        queue = asyncio.Queue()
    stream_queues[chat_id] = queue

def remove_queue_for_chat(chat_id: str):
    logger.info(f"Removing queue for chat_id: {chat_id}")
    stream_queues.pop(chat_id, None)


