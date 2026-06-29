from __future__ import annotations

from dataclasses import dataclass, field, asdict
import json


@dataclass
class ResearchItem:
    title: str
    content: str
    source: str = ""  # "llm_knowledge", "web_search", etc.

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> ResearchItem:
        return cls(**d)


@dataclass
class ResearchPack:
    topic: str
    items: list[ResearchItem] = field(default_factory=list)
    summary: str = ""

    def to_dict(self) -> dict:
        return {
            "topic": self.topic,
            "items": [i.to_dict() for i in self.items],
            "summary": self.summary,
        }

    @classmethod
    def from_dict(cls, d: dict) -> ResearchPack:
        return cls(
            topic=d["topic"],
            items=[ResearchItem.from_dict(i) for i in d.get("items", [])],
            summary=d.get("summary", ""),
        )

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)

    @classmethod
    def from_json(cls, s: str) -> ResearchPack:
        return cls.from_dict(json.loads(s))
