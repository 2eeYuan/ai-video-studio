"""
Pipeline service - orchestrates the full video generation pipeline.
"""
import asyncio
import uuid
from pathlib import Path
from typing import Callable, Optional
from loguru import logger

from services.llm_service import generate_script, generate_terms
from services.subtitle_service import generate_srt_from_text
from services.video_service import combine_videos, overlay_subtitles
from services.aigc.registry import registry
from services.aigc.base import TaskHandle


class PipelineStatus:
    def __init__(self, task_id: str):
        self.task_id = task_id
        self.status = "started"
        self.progress = 0.0
        self.message = ""
        self.video_path: Optional[str] = None
        self.error: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "status": self.status,
            "progress": self.progress,
            "message": self.message,
            "video_path": self.video_path,
            "error": self.error,
        }


# In-memory task store
_tasks: dict[str, PipelineStatus] = {}


def get_task(task_id: str) -> Optional[PipelineStatus]:
    return _tasks.get(task_id)


def get_all_tasks() -> list[dict]:
    return [t.to_dict() for t in _tasks.values()]


async def _generate_clips(
    task_id: str,
    prompts: list[tuple[str, int]],
    output_dir: Path,
    aspect: str,
    update: Callable,
    progress_start: float,
    progress_end: float,
) -> list[str]:
    """Generate AIGC video clips for a list of (prompt, duration) pairs.

    Returns list of local video file paths.
    """
    adapter_name = registry.available[0] if registry.available else "dreamina"
    adapter = registry.get(adapter_name)
    logger.info(f"[{task_id}] Using AIGC adapter: {adapter_name}")

    local_videos = []
    total = len(prompts)
    progress_step = (progress_end - progress_start) / max(total, 1)

    for i, (prompt, duration) in enumerate(prompts):
        prog = progress_start + i * progress_step
        short_prompt = prompt[:40] + "..." if len(prompt) > 40 else prompt
        update(f"生成片段 {i+1}/{total}: {short_prompt}", prog)
        try:
            handle = await adapter.text2video(prompt, duration=duration, ratio=aspect)
            # Poll for completion (max 5 minutes)
            for _ in range(60):
                await asyncio.sleep(5)
                result = await adapter.query_result(handle)
                if result.status == "success" and result.file_path:
                    local_path = await adapter.download(handle, str(output_dir))
                    local_videos.append(local_path)
                    logger.info(f"[{task_id}] Clip {i+1} downloaded: {local_path}")
                    break
                elif result.status == "failed":
                    logger.warning(f"[{task_id}] Clip {i+1} failed: {result.error}")
                    break
            else:
                logger.warning(f"[{task_id}] Clip {i+1} timed out after 5 minutes")
        except Exception as e:
            logger.warning(f"[{task_id}] Clip {i+1} generation error: {e}")
            continue

    return local_videos


async def run_pipeline(
    task_id: str,
    subject: str,
    script: str = "",
    keywords: str = "",
    shots: Optional[list[dict]] = None,
    mode: str = "aigc",
    aspect: str = "9:16",
    clip_duration: int = 3,
    subtitle_config: Optional[dict] = None,
    bgm_config: Optional[dict] = None,
    on_progress: Optional[Callable] = None,
):
    """Run the full video generation pipeline.

    When `shots` is provided (from storyboard), generates AIGC video per shot
    using each shot's description + narration_segment as prompt. AIGC produces
    audio-embedded video, so no separate TTS step is needed.

    When `shots` is empty/None, falls back to legacy keyword-based mode.
    """
    status = PipelineStatus(task_id)
    _tasks[task_id] = status
    output_dir = Path(f"./storage/tasks/{task_id}")
    output_dir.mkdir(parents=True, exist_ok=True)

    def update(msg: str, prog: float):
        status.message = msg
        status.progress = prog
        logger.info(f"[{task_id}] {msg} ({prog:.0%})")
        if on_progress:
            on_progress(task_id, msg, prog)

    try:
        local_videos = []

        if shots:
            # === New mode: per-shot AIGC generation ===
            update("按分镜逐镜头生成视频...", 0.10)
            status.status = "generating_video"

            # Build (prompt, duration) list from shots
            prompts = []
            for shot in shots:
                desc = shot.get("description", "")
                narration = shot.get("narration_segment", "")
                prompt = f"{desc} {narration}".strip()
                duration = shot.get("duration", clip_duration)
                if prompt:
                    prompts.append((prompt, duration))

            if not prompts:
                raise Exception("分镜表中没有有效的画面描述")

            local_videos = await _generate_clips(
                task_id, prompts, output_dir, aspect, update, 0.10, 0.70
            )

            # Generate subtitles from narration text
            if local_videos:
                update("生成字幕...", 0.72)
                status.status = "generating_subtitle"
                all_narration = " ".join(
                    shot.get("narration_segment", "") for shot in shots if shot.get("narration_segment")
                )
                if all_narration.strip():
                    srt_path = str(output_dir / "subtitle.srt")
                    # Estimate total video duration
                    total_duration = sum(shot.get("duration", clip_duration) for shot in shots)
                    generate_srt_from_text(all_narration, total_duration, srt_path)

        else:
            # === Legacy mode: keyword-based generation ===
            from services.tts_service import synthesize
            from services.video_service import add_audio

            # Step 1: Generate script if not provided
            if not script:
                update("生成脚本...", 0.05)
                status.status = "generating_script"
                script = await generate_script(subject=subject)
                if not script:
                    raise Exception("Failed to generate script")

            # Step 2: Generate keywords if not provided
            if not keywords:
                update("生成关键词...", 0.10)
                keyword_list = await generate_terms(subject=subject, script=script)
            else:
                keyword_list = [k.strip() for k in keywords.split(",") if k.strip()]

            # Step 3: Generate audio (TTS)
            update("生成音频...", 0.20)
            status.status = "generating_audio"
            audio_path = str(output_dir / "audio.mp3")
            await synthesize(
                text=script,
                provider="edge-tts",
                voice_name="zh-CN-YunxiNeural",
                output_path=audio_path,
            )

            # Step 4: Generate subtitles
            update("生成字幕...", 0.30)
            status.status = "generating_subtitle"
            srt_path = str(output_dir / "subtitle.srt")
            audio_duration = await _get_audio_duration(audio_path)
            generate_srt_from_text(script, audio_duration, srt_path)

            # Step 5: Generate video clips via AIGC
            update("生成 AIGC 视频片段...", 0.40)
            status.status = "generating_video"
            prompts = [(kw, clip_duration) for kw in keyword_list[:3]]
            local_videos = await _generate_clips(
                task_id, prompts, output_dir, aspect, update, 0.40, 0.60
            )

            if not local_videos:
                raise Exception(
                    f"No AIGC video clips were generated. "
                    f"Check your API key and network connection."
                )

            # Step 6: Combine videos
            update("拼接视频...", 0.65)
            status.status = "combining_video"
            combined_path = str(output_dir / "combined.mp4")
            await combine_videos(local_videos, combined_path)

            # Step 7: Add audio (TTS)
            update("合成音频...", 0.75)
            with_audio_path = str(output_dir / "with_audio.mp4")
            await add_audio(combined_path, audio_path, with_audio_path)

            # Step 8: Overlay subtitles
            update("叠加字幕...", 0.85)
            final_path = str(output_dir / "final.mp4")
            await overlay_subtitles(with_audio_path, srt_path, final_path)

            # Done
            status.status = "done"
            status.video_path = final_path
            status.progress = 1.0
            update("完成!", 1.0)
            logger.info(f"[{task_id}] Pipeline complete: {final_path}")
            return

        # === Common post-processing for shots mode ===
        if not local_videos:
            raise Exception("未能生成任何视频片段，请检查 AIGC API 配置和网络连接")

        # Combine all shot videos
        update("拼接视频...", 0.75)
        status.status = "combining_video"
        combined_path = str(output_dir / "combined.mp4")
        await combine_videos(local_videos, combined_path)

        # Overlay subtitles if available
        srt_path = str(output_dir / "subtitle.srt")
        if Path(srt_path).exists():
            update("叠加字幕...", 0.85)
            final_path = str(output_dir / "final.mp4")
            await overlay_subtitles(combined_path, srt_path, final_path)
        else:
            final_path = combined_path

        # Done
        status.status = "done"
        status.video_path = final_path
        status.progress = 1.0
        update("完成!", 1.0)
        logger.info(f"[{task_id}] Pipeline complete: {final_path}")

    except Exception as e:
        status.status = "failed"
        status.error = str(e)
        status.progress = 0
        logger.error(f"[{task_id}] Pipeline failed: {e}")


async def _get_audio_duration(audio_path: str) -> float:
    """Get audio duration using ffprobe."""
    cmd = [
        "ffprobe",
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        audio_path,
    ]
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, _ = await proc.communicate()
    try:
        return float(stdout.decode().strip())
    except ValueError:
        return 60.0  # Default fallback
