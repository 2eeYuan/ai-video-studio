from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import json

from mymovie.models.story import StoryBrief
from mymovie.models.research import ResearchPack
from mymovie.models.script import Script
from mymovie.models.storyboard import Storyboard
from mymovie.models.prompt import AIGCPrompt
from mymovie.models.segment import Segment


class PipelineState(Enum):
    IDLE = "idle"
    DIALOG = "dialog"
    RESEARCH = "research"
    SCRIPT = "script"
    STORYBOARD = "storyboard"
    PROMPT_GENERATION = "prompt_generation"
    SEGMENTATION = "segmentation"
    VIDEO_GENERATION = "video_generation"
    ASSEMBLY = "assembly"
    REVIEW = "review"
    REVISION = "revision"
    DONE = "done"


@dataclass
class PipelineContext:
    correlation_id: str = ""
    state: PipelineState = PipelineState.IDLE
    story_brief: StoryBrief | None = None
    research_pack: ResearchPack | None = None
    script: Script | None = None
    storyboard: Storyboard | None = None
    prompts: list[AIGCPrompt] = field(default_factory=list)
    segments: list[Segment] = field(default_factory=list)
    video_paths: dict[int, str] = field(default_factory=dict)  # segment_index -> local file path
    final_video_path: str | None = None
    project_dir: Path = field(default_factory=lambda: Path("./projects/default"))
    revision_count: int = 0

    def to_dict(self) -> dict:
        return {
            "correlation_id": self.correlation_id,
            "state": self.state.value,
            "story_brief": self.story_brief.to_dict() if self.story_brief else None,
            "research_pack": self.research_pack.to_dict() if self.research_pack else None,
            "script": self.script.to_dict() if self.script else None,
            "storyboard": self.storyboard.to_dict() if self.storyboard else None,
            "prompts": [p.to_dict() for p in self.prompts],
            "segments": [s.to_dict() for s in self.segments],
            "video_paths": {str(k): v for k, v in self.video_paths.items()},
            "final_video_path": self.final_video_path,
            "project_dir": str(self.project_dir),
            "revision_count": self.revision_count,
        }

    @classmethod
    def from_dict(cls, d: dict) -> PipelineContext:
        ctx = cls()
        ctx.correlation_id = d.get("correlation_id", "")
        ctx.state = PipelineState(d.get("state", "idle"))
        if d.get("story_brief"):
            ctx.story_brief = StoryBrief.from_dict(d["story_brief"])
        if d.get("research_pack"):
            ctx.research_pack = ResearchPack.from_dict(d["research_pack"])
        if d.get("script"):
            ctx.script = Script.from_dict(d["script"])
        if d.get("storyboard"):
            ctx.storyboard = Storyboard.from_dict(d["storyboard"])
        ctx.prompts = [AIGCPrompt.from_dict(p) for p in d.get("prompts", [])]
        ctx.segments = [Segment.from_dict(s) for s in d.get("segments", [])]
        ctx.video_paths = {int(k): v for k, v in d.get("video_paths", {}).items()}
        ctx.final_video_path = d.get("final_video_path")
        ctx.project_dir = Path(d.get("project_dir", "./projects/default"))
        ctx.revision_count = d.get("revision_count", 0)
        return ctx

    def save(self):
        self.project_dir.mkdir(parents=True, exist_ok=True)
        path = self.project_dir / "pipeline_state.json"
        path.write_text(json.dumps(self.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")

    @classmethod
    def load(cls, project_dir: Path) -> PipelineContext:
        path = project_dir / "pipeline_state.json"
        if not path.exists():
            return cls(project_dir=project_dir)
        data = json.loads(path.read_text(encoding="utf-8"))
        ctx = cls.from_dict(data)
        ctx.project_dir = project_dir
        return ctx
