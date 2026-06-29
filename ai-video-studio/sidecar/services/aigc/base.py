"""
AIGC adapter base class.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass
class TaskHandle:
    submit_id: str
    adapter_name: str
    metadata: dict


@dataclass
class TaskResult:
    status: str  # "success", "processing", "failed", "timeout"
    file_path: Optional[str] = None
    error: Optional[str] = None
    raw_response: dict = None


class AIGCAdapter(ABC):
    name: str

    @abstractmethod
    async def text2video(self, prompt: str, duration: int = 5, ratio: str = "9:16") -> TaskHandle:
        """Submit text-to-video generation."""
        ...

    @abstractmethod
    async def query_result(self, handle: TaskHandle) -> TaskResult:
        """Poll for task completion."""
        ...

    @abstractmethod
    async def download(self, handle: TaskHandle, dest_dir: str) -> str:
        """Download completed result. Returns file path."""
        ...
