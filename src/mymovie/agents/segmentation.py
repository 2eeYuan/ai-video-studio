from __future__ import annotations

import logging

from mymovie.agents.base import BaseAgent
from mymovie.bus.message import Message, MessageType
from mymovie.bus.bus import MessageBus
from mymovie.models.prompt import AIGCPrompt
from mymovie.models.segment import Segment

logger = logging.getLogger(__name__)


class SegmentationAgent(BaseAgent):
    name = "segmentation"

    def __init__(self, bus: MessageBus, max_duration: int = 10):
        self.bus = bus
        self.max_duration = max_duration  # max seconds per segment

    def subscribed_types(self) -> list[MessageType]:
        return [MessageType.SEGMENTATION_REQUEST]

    async def handle(self, msg: Message) -> list[Message]:
        prompts: list[AIGCPrompt] = msg.payload.get("prompts", [])

        logger.info(f"SegmentationAgent: splitting {len(prompts)} prompts into segments...")

        segments: list[Segment] = []
        for i, prompt in enumerate(prompts):
            duration = prompt.suggested_duration
            # Clamp to supported durations
            if duration not in (5, 10):
                duration = 10 if duration > 7 else 5

            seg = Segment(
                index=i,
                prompt=prompt.prompt_text,
                duration=duration,
                shot_refs=[prompt.shot_ref],
                status="pending",
            )
            segments.append(seg)

        logger.info(f"SegmentationAgent: created {len(segments)} segments")

        return [Message(
            type=MessageType.SEGMENTS_READY,
            payload={"segments": segments},
            sender=self.name,
            correlation_id=msg.correlation_id,
        )]
