"""
Subtitle service - generates SRT subtitles from TTS word boundaries or Whisper.
"""
import re
from pathlib import Path
from loguru import logger


def generate_srt_from_text(text: str, duration: float, output_path: str) -> str:
    """Generate SRT subtitle file by splitting text into segments."""
    sentences = _split_sentences(text)
    if not sentences:
        return output_path

    # Distribute duration proportionally by text length
    total_chars = sum(len(s) for s in sentences)
    current_time = 0.0

    srt_entries = []
    for i, sentence in enumerate(sentences):
        ratio = len(sentence) / total_chars if total_chars > 0 else 1 / len(sentences)
        seg_duration = duration * ratio
        start = current_time
        end = current_time + seg_duration

        srt_entries.append(
            f"{i + 1}\n"
            f"{_format_time(start)} --> {_format_time(end)}\n"
            f"{sentence.strip()}\n"
        )
        current_time = end

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(srt_entries))

    logger.info(f"Generated SRT: {output_path} ({len(sentences)} entries)")
    return output_path


def _split_sentences(text: str) -> list[str]:
    """Split text into sentences for subtitle display."""
    # Split on Chinese/English punctuation
    parts = re.split(r'([。！？.!?\n])', text)
    sentences = []
    current = ""
    for part in parts:
        if part in "。！？.!?\n":
            current += part
            if current.strip():
                sentences.append(current.strip())
            current = ""
        else:
            current += part
    if current.strip():
        sentences.append(current.strip())

    # Merge very short segments
    merged = []
    for s in sentences:
        if merged and len(merged[-1]) < 10:
            merged[-1] += s
        else:
            merged.append(s)
    return merged


def _format_time(seconds: float) -> str:
    """Format seconds to SRT time format (HH:MM:SS,mmm)."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"
