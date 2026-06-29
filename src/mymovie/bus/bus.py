from __future__ import annotations

import asyncio
import logging
from collections import defaultdict

from mymovie.bus.message import Message, MessageType

logger = logging.getLogger(__name__)


class MessageBus:
    def __init__(self):
        self._subscribers: dict[MessageType, list[asyncio.Queue]] = defaultdict(list)
        self._agent_queues: dict[str, asyncio.Queue] = {}

    def register(self, agent_name: str, message_types: list[MessageType]) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue()
        self._agent_queues[agent_name] = queue
        for mt in message_types:
            self._subscribers[mt].append(queue)
        logger.debug(f"Agent '{agent_name}' registered for {[mt.value for mt in message_types]}")
        return queue

    async def publish(self, message: Message):
        subscribers = self._subscribers.get(message.type, [])
        if not subscribers:
            logger.warning(f"No subscribers for message type '{message.type.value}' from '{message.sender}'")
            return
        for queue in subscribers:
            await queue.put(message)
        logger.debug(f"Published '{message.type.value}' from '{message.sender}' to {len(subscribers)} subscriber(s)")

    def get_queue(self, agent_name: str) -> asyncio.Queue:
        return self._agent_queues[agent_name]
