from __future__ import annotations

import asyncio
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class FFmpegError(Exception):
    pass


async def concat_videos_demuxer(video_paths: list[str], output_path: str) -> str:
    """Concatenate videos using the demuxer method (fast, no re-encode).
    All input videos must have the same codec, resolution, and framerate."""
    list_file = Path(output_path).parent / "concat_list.txt"
    list_file.write_text(
        "\n".join(f"file '{p}'" for p in video_paths),
        encoding="utf-8",
    )

    cmd = [
        "ffmpeg", "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", str(list_file),
        "-c", "copy",
        output_path,
    ]

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()

    if proc.returncode != 0:
        raise FFmpegError(f"FFmpeg concat failed: {stderr.decode()}")

    list_file.unlink(missing_ok=True)
    logger.info(f"Concatenated {len(video_paths)} videos -> {output_path}")
    return output_path


async def concat_videos_filter(video_paths: list[str], output_path: str, codec: str = "libx264") -> str:
    """Concatenate videos using the filter method (slower, handles different formats)."""
    inputs = []
    for p in video_paths:
        inputs.extend(["-i", p])

    filter_parts = []
    for i in range(len(video_paths)):
        filter_parts.append(f"[{i}:v:0][{i}:a:0]")
    filter_str = "".join(filter_parts) + f"concat=n={len(video_paths)}:v=1:a=1[outv][outa]"

    cmd = [
        "ffmpeg", "-y",
        *inputs,
        "-filter_complex", filter_str,
        "-map", "[outv]",
        "-map", "[outa]",
        "-c:v", codec,
        "-c:a", "aac",
        output_path,
    ]

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()

    if proc.returncode != 0:
        raise FFmpegError(f"FFmpeg filter concat failed: {stderr.decode()}")

    logger.info(f"Filter-concatenated {len(video_paths)} videos -> {output_path}")
    return output_path


async def concat_videos(video_paths: list[str], output_path: str, method: str = "demuxer", codec: str = "libx264") -> str:
    """Concatenate videos. Tries demuxer first, falls back to filter on failure."""
    if method == "demuxer":
        try:
            return await concat_videos_demuxer(video_paths, output_path)
        except FFmpegError:
            logger.warning("Demuxer concat failed, falling back to filter method")
            return await concat_videos_filter(video_paths, output_path, codec)
    else:
        return await concat_videos_filter(video_paths, output_path, codec)
