from __future__ import annotations

import asyncio
import logging
from abc import ABC, abstractmethod

from mymovie.bus.message import Message, MessageType
from mymovie.bus.bus import MessageBus

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    name: str
    bus: MessageBus

    @abstractmethod
    def subscribed_types(self) -> list[MessageType]:
        """Return the message types this agent wants to receive."""
        ...

    @abstractmethod
    async def handle(self, msg: Message) -> list[Message]:
        """Process one message, return zero or more outgoing messages."""
        ...

    async def start(self):
        """Register on the bus and process messages until cancelled."""
        queue = self.bus.register(self.name, self.subscribed_types())
        logger.info(f"Agent '{self.name}' started")
        try:
            while True:
                msg = await queue.get()
                try:
                    responses = await self.handle(msg)
                    for r in responses:
                        await self.bus.publish(r)
                except Exception as e:
                    logger.error(f"Agent '{self.name}' error handling {msg.type.value}: {e}", exc_info=True)
                    await self.bus.publish(Message(
                        type=MessageType.AGENT_ERROR,
                        payload={"agent": self.name, "error": str(e), "recoverable": True},
                        sender=self.name,
                        correlation_id=msg.correlation_id,
                    ))
        except asyncio.CancelledError:
            logger.info(f"Agent '{self.name}' stopped")
