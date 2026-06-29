from __future__ import annotations

import logging
from pathlib import Path

from mymovie.agents.base import BaseAgent
from mymovie.bus.message import Message, MessageType
from mymovie.bus.bus import MessageBus
from mymovie.models.story import StoryBrief
from mymovie.models.research import ResearchPack
from mymovie.models.script import Script
from mymovie.utils.llm import LLMClient

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = Path(__file__).parent.parent.joinpath("prompts/scriptwriter_system.txt").read_text(encoding="utf-8")


class ScriptwriterAgent(BaseAgent):
    name = "scriptwriter"

    def __init__(self, bus: MessageBus, llm: LLMClient):
        self.bus = bus
        self.llm = llm

    def subscribed_types(self) -> list[MessageType]:
        return [MessageType.SCRIPT_REQUEST]

    async def handle(self, msg: Message) -> list[Message]:
        story_brief = msg.payload.get("story_brief")
        research_pack = msg.payload.get("research_pack")

        logger.info("ScriptwriterAgent: writing script...")

        user_prompt = f"故事概要：\n{story_brief.to_json()}\n\n"
        if research_pack:
            user_prompt += f"研究资料：\n{research_pack.to_json()}\n\n"
        user_prompt += "请根据以上信息编写完整的视频剧本。"

        script_dict = await self.llm.chat_json(SYSTEM_PROMPT, user_prompt)
        script = Script.from_dict(script_dict)

        logger.info(f"ScriptwriterAgent: script '{script.title}' with {len(script.scenes)} scenes")

        return [Message(
            type=MessageType.SCRIPT_READY,
            payload={"script": script},
            sender=self.name,
            correlation_id=msg.correlation_id,
        )]
