from __future__ import annotations

import logging
from pathlib import Path

from mymovie.agents.base import BaseAgent
from mymovie.bus.message import Message, MessageType
from mymovie.bus.bus import MessageBus
from mymovie.models.script import Script
from mymovie.models.storyboard import Storyboard
from mymovie.utils.llm import LLMClient

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = Path(__file__).parent.parent.joinpath("prompts/storyboard_system.txt").read_text(encoding="utf-8")


class StoryboardAgent(BaseAgent):
    name = "storyboard"

    def __init__(self, bus: MessageBus, llm: LLMClient):
        self.bus = bus
        self.llm = llm

    def subscribed_types(self) -> list[MessageType]:
        return [MessageType.STORYBOARD_REQUEST]

    async def handle(self, msg: Message) -> list[Message]:
        script = msg.payload.get("script")

        logger.info("StoryboardAgent: creating storyboard...")

        user_prompt = f"剧本：\n{script.to_json()}\n\n请根据剧本创建详细的分镜脚本。"
        storyboard_dict = await self.llm.chat_json(SYSTEM_PROMPT, user_prompt)
        storyboard = Storyboard.from_dict(storyboard_dict)

        logger.info(f"StoryboardAgent: {len(storyboard.shots)} shots, ~{storyboard.total_estimated_duration}s")

        return [Message(
            type=MessageType.STORYBOARD_READY,
            payload={"storyboard": storyboard},
            sender=self.name,
            correlation_id=msg.correlation_id,
        )]
