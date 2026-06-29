from __future__ import annotations

from dataclasses import dataclass, field, asdict
import json


@dataclass
class CameraMove:
    type: str = "static"  # "static", "pan_left", "pan_right", "dolly_in", "dolly_out", "tracking", "zoom_in", "zoom_out"
    speed: str = "medium"  # "slow", "medium", "fast"
    start_frame: str = ""  # wide description of start framing
    end_frame: str = ""  # wide description of end framing

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> CameraMove:
        return cls(**d)


@dataclass
class Shot:
    shot_number: int
    scene_ref: int  # which scene this belongs to
    description: str  # what happens in this shot
    camera: CameraMove = field(default_factory=CameraMove)
    duration_seconds: int = 5
    music_cue: str | None = None
    sound_effect: str | None = None
    visual_notes: str = ""  # lighting, color, style notes

    def to_dict(self) -> dict:
        return {
            "shot_number": self.shot_number,
            "scene_ref": self.scene_ref,
            "description": self.description,
            "camera": self.camera.to_dict(),
            "duration_seconds": self.duration_seconds,
            "music_cue": self.music_cue,
            "sound_effect": self.sound_effect,
            "visual_notes": self.visual_notes,
        }

    @classmethod
    def from_dict(cls, d: dict) -> Shot:
        return cls(
            shot_number=d["shot_number"],
            scene_ref=d["scene_ref"],
            description=d["description"],
            camera=CameraMove.from_dict(d.get("camera", {})),
            duration_seconds=d.get("duration_seconds", 5),
            music_cue=d.get("music_cue"),
            sound_effect=d.get("sound_effect"),
            visual_notes=d.get("visual_notes", ""),
        )


@dataclass
class Storyboard:
    shots: list[Shot] = field(default_factory=list)
    total_estimated_duration: int = 0

    def to_dict(self) -> dict:
        return {
            "shots": [s.to_dict() for s in self.shots],
            "total_estimated_duration": self.total_estimated_duration,
        }

    @classmethod
    def from_dict(cls, d: dict) -> Storyboard:
        return cls(
            shots=[Shot.from_dict(s) for s in d.get("shots", [])],
            total_estimated_duration=d.get("total_estimated_duration", 0),
        )

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)

    @classmethod
    def from_json(cls, s: str) -> Storyboard:
        return cls.from_dict(json.loads(s))
