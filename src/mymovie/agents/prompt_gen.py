from __future__ import annotations

import logging
from pathlib import Path

from mymovie.agents.base import BaseAgent
from mymovie.bus.message import Message, MessageType
from mymovie.bus.bus import MessageBus
from mymovie.models.storyboard import Storyboard
from mymovie.models.prompt import AIGCPrompt
from mymovie.utils.llm import LLMClient

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = Path(__file__).parent.parent.joinpath("prompts/prompt_gen_system.txt").read_text(encoding="utf-8")


class PromptAgent(BaseAgent):
    name = "prompt_gen"

    def __init__(self, bus: MessageBus, llm: LLMClient):
        self.bus = bus
        self.llm = llm

    def subscribed_types(self) -> list[MessageType]:
        return [MessageType.PROMPT_REQUEST]

    async def handle(self, msg: Message) -> list[Message]:
        storyboard = msg.payload.get("storyboard")

        logger.info("PromptAgent: generating AIGC prompts...")

        user_prompt = f"分镜脚本：\n{storyboard.to_json()}\n\n请将每个镜头转换为AIGC视频生成prompt。"
        result = await self.llm.chat_json(SYSTEM_PROMPT, user_prompt)

        prompts = [AIGCPrompt.from_dict(p) for p in result.get("prompts", [])]

        logger.info(f"PromptAgent: generated {len(prompts)} AIGC prompts")

        return [Message(
            type=MessageType.PROMPTS_READY,
            payload={"prompts": prompts},
            sender=self.name,
            correlation_id=msg.correlation_id,
        )]
