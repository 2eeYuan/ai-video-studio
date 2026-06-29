"""
Video service - combines video clips with FFmpeg.
"""
import asyncio
import subprocess
from pathlib import Path
from loguru import logger


async def combine_videos(
    video_paths: list[str],
    output_path: str,
    method: str = "demuxer",
    codec: str = "libx264",
) -> str:
    """Combine multiple video clips into one."""
    if not video_paths:
        raise ValueError("No video paths provided")

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    if method == "demuxer":
        try:
            return await _concat_demuxer(video_paths, output_path)
        except Exception as e:
            logger.warning(f"Demuxer concat failed: {e}, falling back to filter")
            return await _concat_filter(video_paths, output_path, codec)
    else:
        return await _concat_filter(video_paths, output_path, codec)


async def _concat_demuxer(video_paths: list[str], output_path: str) -> str:
    """Concatenate using demuxer (fast, no re-encode)."""
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
    _, stderr = await proc.communicate()

    list_file.unlink(missing_ok=True)

    if proc.returncode != 0:
        raise Exception(f"FFmpeg concat failed: {stderr.decode()}")

    logger.info(f"Combined {len(video_paths)} videos -> {output_path}")
    return output_path


async def _concat_filter(video_paths: list[str], output_path: str, codec: str) -> str:
    """Concatenate using filter (handles different formats)."""
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
    _, stderr = await proc.communicate()

    if proc.returncode != 0:
        raise Exception(f"FFmpeg filter concat failed: {stderr.decode()}")

    logger.info(f"Filter-combined {len(video_paths)} videos -> {output_path}")
    return output_path


async def overlay_subtitles(video_path: str, srt_path: str, output_path: str) -> str:
    """Overlay SRT subtitles on video."""
    cmd = [
        "ffmpeg", "-y",
        "-i", video_path,
        "-vf", f"subtitles={srt_path}:force_style='FontSize=24,PrimaryColour=&Hffffff&,OutlineColour=&H000000&,Outline=2'",
        "-c:a", "copy",
        output_path,
    ]

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await proc.communicate()

    if proc.returncode != 0:
        raise Exception(f"Subtitle overlay failed: {stderr.decode()}")

    logger.info(f"Overlaid subtitles -> {output_path}")
    return output_path


async def add_audio(video_path: str, audio_path: str, output_path: str, bgm_path: str = "", bgm_volume: float = 0.2) -> str:
    """Mix audio into video, optionally with background music."""
    if bgm_path:
        cmd = [
            "ffmpeg", "-y",
            "-i", video_path,
            "-i", audio_path,
            "-i", bgm_path,
            "-filter_complex",
            f"[1:a]volume=1.0[voice];[2:a]volume={bgm_volume}[bgm];[voice][bgm]amix=inputs=2:duration=first[aout]",
            "-map", "0:v",
            "-map", "[aout]",
            "-c:v", "copy",
            "-shortest",
            output_path,
        ]
    else:
        cmd = [
            "ffmpeg", "-y",
            "-i", video_path,
            "-i", audio_path,
            "-map", "0:v",
            "-map", "1:a",
            "-c:v", "copy",
            "-shortest",
            output_path,
        ]

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await proc.communicate()

    if proc.returncode != 0:
        raise Exception(f"Audio mixing failed: {stderr.decode()}")

    logger.info(f"Added audio -> {output_path}")
    return output_path
