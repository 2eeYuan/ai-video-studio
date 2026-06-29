from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class LLMConfig:
    base_url: str = "https://token-plan-cn.xiaomimimo.com/anthropic"
    api_key: str = ""
    model: str = "mimo-2.5-pro"
    max_tokens: int = 4096
    temperature: float = 0.7


@dataclass
class DreaminaConfig:
    download_dir: str = "./downloads"
    poll_timeout: int = 60
    max_retries: int = 3


@dataclass
class AdaptersConfig:
    default: str = "dreamina"
    dreamina: DreaminaConfig = field(default_factory=DreaminaConfig)


@dataclass
class FFmpegConfig:
    concat_method: str = "demuxer"
    output_codec: str = "libx264"
    output_format: str = "mp4"


@dataclass
class VideoConfig:
    default_duration: int = 60
    segment_durations: list[int] = field(default_factory=lambda: [5, 10])
    default_ratio: str = "16:9"
    default_resolution: str = "720P"
    ffmpeg: FFmpegConfig = field(default_factory=FFmpegConfig)


@dataclass
class ProjectsConfig:
    base_dir: str = "./projects"


@dataclass
class AppConfig:
    llm: LLMConfig = field(default_factory=LLMConfig)
    adapters: AdaptersConfig = field(default_factory=AdaptersConfig)
    video: VideoConfig = field(default_factory=VideoConfig)
    projects: ProjectsConfig = field(default_factory=ProjectsConfig)


def _resolve_env_vars(value: str) -> str:
    """Resolve ${VAR} patterns in string values."""
    if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
        env_name = value[2:-1]
        return os.environ.get(env_name, value)
    return value


def _apply_env_vars(obj):
    """Recursively resolve env vars in config."""
    if isinstance(obj, dict):
        return {k: _apply_env_vars(v) for k, v in obj.items()}
    elif isinstance(obj, str):
        return _resolve_env_vars(obj)
    elif isinstance(obj, list):
        return [_apply_env_vars(v) for v in obj]
    return obj


def load_config(config_path: str | Path = "config.yaml") -> AppConfig:
    """Load configuration from YAML file with environment variable substitution."""
    path = Path(config_path)
    if not path.exists():
        return AppConfig()

    with open(path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}

    raw = _apply_env_vars(raw)

    config = AppConfig()
    if "llm" in raw:
        config.llm = LLMConfig(**{k: v for k, v in raw["llm"].items() if hasattr(LLMConfig, k)})
    if "adapters" in raw:
        adapters_raw = raw["adapters"]
        config.adapters = AdaptersConfig(
            default=adapters_raw.get("default", "dreamina"),
            dreamina=DreaminaConfig(**{k: v for k, v in adapters_raw.get("dreamina", {}).items() if hasattr(DreaminaConfig, k)}),
        )
    if "video" in raw:
        video_raw = raw["video"]
        ffmpeg_raw = video_raw.pop("ffmpeg", {})
        config.video = VideoConfig(
            **{k: v for k, v in video_raw.items() if hasattr(VideoConfig, k)},
            ffmpeg=FFmpegConfig(**{k: v for k, v in ffmpeg_raw.items() if hasattr(FFmpegConfig, k)}),
        )
    if "projects" in raw:
        config.projects = ProjectsConfig(**{k: v for k, v in raw["projects"].items() if hasattr(ProjectsConfig, k)})

    return config
