from __future__ import annotations

from dataclasses import dataclass, field, asdict
import json


@dataclass
class CharacterDesc:
    name: str
    role: str  # "protagonist", "antagonist", "supporting", etc.
    appearance: str
    key_traits: str

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> CharacterDesc:
        return cls(**d)


@dataclass
class StoryBrief:
    topic: str
    genre: str  # e.g., "sci-fi short", "documentary", "historical drama"
    setting: str  # time and place
    characters: list[CharacterDesc] = field(default_factory=list)
    tone: str = ""  # e.g., "dark", "comedic", "epic"
    target_duration_seconds: int = 60
    visual_style: str = "cinematic"  # e.g., "cinematic", "anime", "realistic"
    additional_notes: str = ""

    def to_dict(self) -> dict:
        d = asdict(self)
        d["characters"] = [c.to_dict() for c in self.characters]
        return d

    @classmethod
    def from_dict(cls, d: dict) -> StoryBrief:
        d = d.copy()
        d["characters"] = [CharacterDesc.from_dict(c) for c in d.get("characters", [])]
        return cls(**d)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)

    @classmethod
    def from_json(cls, s: str) -> StoryBrief:
        return cls.from_dict(json.loads(s))
