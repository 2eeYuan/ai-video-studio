from __future__ import annotations

import logging
from pathlib import Path

from mymovie.agents.base import BaseAgent
from mymovie.bus.message import Message, MessageType
from mymovie.bus.bus import MessageBus
from mymovie.models.story import StoryBrief
from mymovie.models.research import ResearchPack
from mymovie.utils.llm import LLMClient

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = Path(__file__).parent.parent.joinpath("prompts/research_system.txt").read_text(encoding="utf-8")


class ResearchAgent(BaseAgent):
    name = "research"

    def __init__(self, bus: MessageBus, llm: LLMClient):
        self.bus = bus
        self.llm = llm

    def subscribed_types(self) -> list[MessageType]:
        return [MessageType.RESEARCH_REQUEST]

    async def handle(self, msg: Message) -> list[Message]:
        story_brief = msg.payload.get("story_brief")
        if not story_brief:
            return []

        logger.info(f"ResearchAgent: researching '{story_brief.topic}'...")

        user_prompt = f"请为以下视频项目搜集背景资料：\n\n{story_brief.to_json()}"
        research_dict = await self.llm.chat_json(SYSTEM_PROMPT, user_prompt)

        research_pack = ResearchPack.from_dict(research_dict)
        research_pack.topic = story_brief.topic

        logger.info(f"ResearchAgent: found {len(research_pack.items)} research items")

        return [Message(
            type=MessageType.RESEARCH_COMPLETE,
            payload={"research_pack": research_pack},
            sender=self.name,
            correlation_id=msg.correlation_id,
        )]
