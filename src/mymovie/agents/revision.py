from __future__ import annotations

import logging
from pathlib import Path

from mymovie.agents.base import BaseAgent
from mymovie.bus.message import Message, MessageType
from mymovie.bus.bus import MessageBus
from mymovie.models.revision import RevisionPlan
from mymovie.utils.llm import LLMClient

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = Path(__file__).parent.parent.joinpath("prompts/revision_system.txt").read_text(encoding="utf-8")


class RevisionAgent(BaseAgent):
    name = "revision"

    def __init__(self, bus: MessageBus, llm: LLMClient):
        self.bus = bus
        self.llm = llm

    def subscribed_types(self) -> list[MessageType]:
        return [MessageType.REVISION_REQUEST]

    async def handle(self, msg: Message) -> list[Message]:
        feedback = msg.payload.get("feedback", "")
        script = msg.payload.get("script")
        storyboard = msg.payload.get("storyboard")
        segments = msg.payload.get("segments", [])

        logger.info(f"RevisionAgent: analyzing feedback: '{feedback[:100]}...'")

        # Build context for the LLM
        segments_info = []
        for seg in segments:
            segments_info.append({
                "index": seg.index,
                "prompt": seg.prompt,
                "duration": seg.duration,
                "status": seg.status,
            })

        user_prompt = f"""用户反馈: {feedback}

当前剧本摘要:
{script.to_json() if script else '无'}

当前分镜摘要:
{storyboard.to_json() if storyboard else '无'}

当前视频段落:
{segments_info}

请根据用户反馈，确定需要修改哪些段落，并生成修改计划。"""

        plan_dict = await self.llm.chat_json(SYSTEM_PROMPT, user_prompt)
        revision_plan = RevisionPlan.from_dict(plan_dict)

        logger.info(f"RevisionAgent: {len(revision_plan.segments_to_regenerate)} to regenerate, "
                    f"{len(revision_plan.segments_to_add)} to add, "
                    f"{len(revision_plan.segments_to_remove)} to remove")

        if revision_plan.notes:
            print(f"\n📋 修改计划: {revision_plan.notes}\n")

        return [Message(
            type=MessageType.REVISION_SEGMENTS_READY,
            payload={"revision_plan": revision_plan},
            sender=self.name,
            correlation_id=msg.correlation_id,
        )]
