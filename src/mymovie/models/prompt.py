from __future__ import annotations

from dataclasses import dataclass, field, asdict
import json


@dataclass
class AIGCPrompt:
    shot_ref: int  # which storyboard shot this corresponds to
    prompt_text: str  # the actual text sent to AIGC tool
    negative_prompt: str = ""
    suggested_duration: int = 5  # 5 or 10
    tool_type: str = "text2video"  # "text2video" or "text2image"
    visual_style_tags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> AIGCPrompt:
        return cls(**d)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)

    @classmethod
    def from_json(cls, s: str) -> AIGCPrompt:
        return cls.from_dict(json.loads(s))
