from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum


class MessageType(Enum):
    # Pipeline control
    PIPELINE_START = "pipeline_start"
    DIALOG_TURN = "dialog_turn"
    STORY_DETAILS_READY = "story_details_ready"
    RESEARCH_REQUEST = "research_request"
    RESEARCH_COMPLETE = "research_complete"
    SCRIPT_REQUEST = "script_request"
    SCRIPT_READY = "script_ready"
    STORYBOARD_REQUEST = "storyboard_request"
    STORYBOARD_READY = "storyboard_ready"
    PROMPT_REQUEST = "prompt_request"
    PROMPTS_READY = "prompts_ready"
    SEGMENTATION_REQUEST = "segmentation_request"
    SEGMENTS_READY = "segments_ready"
    VIDEOGEN_REQUEST = "videogen_request"
    VIDEOGEN_SEGMENT_DONE = "videogen_segment_done"
    VIDEOGEN_ALL_DONE = "videogen_all_done"
    ASSEMBLY_REQUEST = "assembly_request"
    ASSEMBLY_DONE = "assembly_done"
    REVIEW_REQUEST = "review_request"
    REVISION_REQUEST = "revision_request"
    REVISION_SEGMENTS_READY = "revision_segments_ready"
    PIPELINE_COMPLETE = "pipeline_complete"

    # Error / control
    AGENT_ERROR = "agent_error"
    PIPELINE_CANCEL = "pipeline_cancel"


@dataclass
class Message:
    type: MessageType
    payload: dict = field(default_factory=dict)
    sender: str = ""
    correlation_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    timestamp: float = field(default_factory=time.time)
    reply_to: MessageType | None = None

    def reply(self, msg_type: MessageType, payload: dict, sender: str) -> Message:
        return Message(
            type=msg_type,
            payload=payload,
            sender=sender,
            correlation_id=self.correlation_id,
            reply_to=self.type,
        )
