from __future__ import annotations

import logging
from pathlib import Path

from mymovie.agents.base import BaseAgent
from mymovie.bus.message import Message, MessageType
from mymovie.bus.bus import MessageBus
from mymovie.config import FFmpegConfig
from mymovie.utils.ffmpeg import concat_videos, FFmpegError

logger = logging.getLogger(__name__)


class AssemblyAgent(BaseAgent):
    name = "assembly"

    def __init__(self, bus: MessageBus, ffmpeg_config: FFmpegConfig, project_dir: Path):
        self.bus = bus
        self.ffmpeg_config = ffmpeg_config
        self.project_dir = project_dir

    def subscribed_types(self) -> list[MessageType]:
        return [MessageType.ASSEMBLY_REQUEST]

    async def handle(self, msg: Message) -> list[Message]:
        video_paths: list[str] = msg.payload.get("video_paths", [])

        if not video_paths:
            return [Message(
                type=MessageType.AGENT_ERROR,
                payload={"agent": self.name, "error": "No video paths to assemble", "recoverable": False},
                sender=self.name,
                correlation_id=msg.correlation_id,
            )]

        logger.info(f"AssemblyAgent: concatenating {len(video_paths)} video segments...")

        output_path = str(self.project_dir / "final.mp4")

        try:
            await concat_videos(
                video_paths=video_paths,
                output_path=output_path,
                method=self.ffmpeg_config.concat_method,
                codec=self.ffmpeg_config.output_codec,
            )
            logger.info(f"AssemblyAgent: final video -> {output_path}")

            return [Message(
                type=MessageType.ASSEMBLY_DONE,
                payload={"output_path": output_path, "segment_count": len(video_paths)},
                sender=self.name,
                correlation_id=msg.correlation_id,
            )]
        except FFmpegError as e:
            logger.error(f"AssemblyAgent: FFmpeg error: {e}")
            return [Message(
                type=MessageType.AGENT_ERROR,
                payload={"agent": self.name, "error": str(e), "recoverable": True},
                sender=self.name,
                correlation_id=msg.correlation_id,
            )]
