from __future__ import annotations

from dataclasses import dataclass, field, asdict
import json


@dataclass
class DialogueLine:
    character: str
    line: str
    direction: str = ""  # e.g., "(whispering)", "(shouting)"

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> DialogueLine:
        return cls(**d)


@dataclass
class Scene:
    scene_number: int
    location: str
    time_of_day: str
    characters_present: list[str] = field(default_factory=list)
    action: str = ""  # stage directions
    dialogue: list[DialogueLine] = field(default_factory=list)
    estimated_duration_seconds: int = 10
    mood: str = ""

    def to_dict(self) -> dict:
        return {
            "scene_number": self.scene_number,
            "location": self.location,
            "time_of_day": self.time_of_day,
            "characters_present": self.characters_present,
            "action": self.action,
            "dialogue": [d.to_dict() for d in self.dialogue],
            "estimated_duration_seconds": self.estimated_duration_seconds,
            "mood": self.mood,
        }

    @classmethod
    def from_dict(cls, d: dict) -> Scene:
        return cls(
            scene_number=d["scene_number"],
            location=d["location"],
            time_of_day=d["time_of_day"],
            characters_present=d.get("characters_present", []),
            action=d.get("action", ""),
            dialogue=[DialogueLine.from_dict(dl) for dl in d.get("dialogue", [])],
            estimated_duration_seconds=d.get("estimated_duration_seconds", 10),
            mood=d.get("mood", ""),
        )


@dataclass
class Script:
    title: str
    synopsis: str
    scenes: list[Scene] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "synopsis": self.synopsis,
            "scenes": [s.to_dict() for s in self.scenes],
        }

    @classmethod
    def from_dict(cls, d: dict) -> Script:
        return cls(
            title=d["title"],
            synopsis=d["synopsis"],
            scenes=[Scene.from_dict(s) for s in d.get("scenes", [])],
        )

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)

    @classmethod
    def from_json(cls, s: str) -> Script:
        return cls.from_dict(json.loads(s))
