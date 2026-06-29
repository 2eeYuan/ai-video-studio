from __future__ import annotations

from dataclasses import dataclass, field, asdict
import json


@dataclass
class SegmentRevision:
    segment_index: int
    new_prompt: str
    reason: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> SegmentRevision:
        return cls(**d)


@dataclass
class SegmentAddition:
    insert_after: int  # insert after this segment index
    prompt: str
    duration: int = 5
    reason: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> SegmentAddition:
        return cls(**d)


@dataclass
class RevisionPlan:
    segments_to_regenerate: list[SegmentRevision] = field(default_factory=list)
    segments_to_add: list[SegmentAddition] = field(default_factory=list)
    segments_to_remove: list[int] = field(default_factory=list)
    notes: str = ""  # explanation for the user

    def to_dict(self) -> dict:
        return {
            "segments_to_regenerate": [s.to_dict() for s in self.segments_to_regenerate],
            "segments_to_add": [s.to_dict() for s in self.segments_to_add],
            "segments_to_remove": self.segments_to_remove,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, d: dict) -> RevisionPlan:
        return cls(
            segments_to_regenerate=[SegmentRevision.from_dict(s) for s in d.get("segments_to_regenerate", [])],
            segments_to_add=[SegmentAddition.from_dict(s) for s in d.get("segments_to_add", [])],
            segments_to_remove=d.get("segments_to_remove", []),
            notes=d.get("notes", ""),
        )

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)

    @classmethod
    def from_json(cls, s: str) -> RevisionPlan:
        return cls.from_dict(json.loads(s))
