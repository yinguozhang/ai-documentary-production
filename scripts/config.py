"""Shared machine-readable project/provider config helpers."""

from __future__ import annotations

import json
import sys
from pathlib import Path

DEFAULT_PROJECT = {
    "title": "",
    "subtitle": "",
    "profile": "short",
    "model_routing": "hybrid",
    "image_mode": "human",
    "duration_target_sec": 30,
    "shot_target": 12,
    "segment_target": 2,
    "opening_card": "none",
    "opening_seconds": 3.0,
    "opening_in_target": True,
    "aspect": "16:9",
    "resolution": "1920x1080",
    "fps": 30,
    "language": "zh-CN",
    "audience": "",
    "platform": "",
    "deadline": "",
    "budget_cny": 0,
    "providers": {
        "image": "user_gpt",
        "video": "minimax_h3",
        "voice": "capcut_tts",
        "music": "local_midi_fluidsynth",
        "edit": "capcut",
        "qc": "ffmpeg",
    },
    "rights": {"historical_photos": "", "music": "", "ai_disclosure": True},
}

DEFAULT_PROVIDERS = {
    "image": {"provider": "user_gpt", "mode": "human", "output": "first_frame.png"},
    "video": {
        "provider": "minimax_h3",
        "base_url": "https://api.minimax.cn",
        "api_key_env": "MINIMAX_API_KEY",
        "model": "MiniMax-H3",
        "fallback_model": "MiniMax-H3-Max",
        "resolution": "768P",
        "duration": "4-15",
        "takes": 1,
        "fallback": "minimax_h3_max",
    },
    "voice": {"provider": "capcut_tts", "output": "vo.wav", "sample_rate": 48000},
    "music": {
        "provider": "local_midi_fluidsynth",
        "output": "music_sections/",
        "sample_rate": 48000,
        "bit_depth": 24,
    },
    "edit": {"provider": "capcut", "resolution": "1920x1080", "fps": 30},
    "qc": {"provider": "ffmpeg"},
}

PROFILES = {
    "short": {"duration_target_sec": 30, "shot_target": 12, "segment_target": 2, "music_sections": 1},
    "standard": {"duration_target_sec": 180, "shot_target": 48, "segment_target": 4, "music_sections": 5},
}


def fail(message: str) -> "NoReturn":
    print(f"error: {message}", file=sys.stderr)
    raise SystemExit(1)


def load_json(path: Path, default: dict) -> dict:
    if not path.is_file():
        fail(f"config not found: {path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        fail(f"invalid JSON config {path}: {exc}")
    if not isinstance(data, dict):
        fail(f"config must be a JSON object: {path}")
    merged = dict(default)
    merged.update(data)
    return merged


def load_project(path: Path) -> dict:
    return load_json(path, DEFAULT_PROJECT)


def load_providers(path: Path) -> dict:
    return load_json(path, DEFAULT_PROVIDERS)


def resolution(value: str) -> tuple[int, int]:
    try:
        width, height = str(value).lower().replace("×", "x").split("x", 1)
        return int(width), int(height)
    except (ValueError, AttributeError):
        fail(f"invalid resolution: {value!r}; expected 1920x1080")
