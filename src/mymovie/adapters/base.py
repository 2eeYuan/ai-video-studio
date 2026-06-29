from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
import time


class AIGCAdapterError(Exception):
    pass


@dataclass
class TaskHandle:
    submit_id: str
    adapter_name: str
    submitted_at: float = field(default_factory=time.time)
    metadata: dict = field(default_factory=dict)


@dataclass
class TaskResult:
    status: str  # "success", "querying", "failed", "timeout"
    file_path: str | None = None
    error: str | None = None
    raw_response: dict = field(default_factory=dict)


class AIGCAdapter(ABC):
    name: str

    @abstractmethod
    async def text2video(self, prompt: str, duration: int,
                         ratio: str = "16:9", resolution: str = "720P") -> TaskHandle:
        """Submit text-to-video generation. Returns a handle for polling."""
        ...

    @abstractmethod
    async def text2image(self, prompt: str, ratio: str = "1:1",
                         resolution: str = "2k") -> TaskHandle:
        """Submit text-to-image generation."""
        ...

    @abstractmethod
    async def image2video(self, image_path: str, prompt: str,
                          duration: int) -> TaskHandle:
        """Submit image-to-video generation."""
        ...

    @abstractmethod
    async def query_result(self, handle: TaskHandle) -> TaskResult:
        """Poll for task completion."""
        ...

    @abstractmethod
    async def download(self, handle: TaskHandle, dest_dir: str) -> str:
        """Download completed result to local path. Returns file path."""
        ...

    @abstractmethod
    def supported_durations(self) -> list[int]:
        """Return [5, 10] or whatever this tool supports."""
        ...

    @abstractmethod
    def max_prompt_length(self) -> int:
        """Return max characters for prompt."""
        ...
