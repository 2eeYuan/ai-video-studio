from __future__ import annotations

from dataclasses import dataclass, field, asdict
import json


@dataclass
class Segment:
    index: int  # stable position in the final video
    prompt: str  # current AIGC prompt
    duration: int = 5  # 5 or 10
    shot_refs: list[int] = field(default_factory=list)  # storyboard shot indices
    video_path: str | None = None
    status: str = "pending"  # "pending", "generating", "done", "failed", "revised"
    submit_id: str | None = None  # AIGC task ID
    generation_attempts: int = 0
    error_log: list[str] = field(default_factory=list)
    adapter_name: str = "dreamina"

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> Segment:
        return cls(**d)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)

    @classmethod
    def from_json(cls, s: str) -> Segment:
        return cls.from_dict(json.loads(s))
