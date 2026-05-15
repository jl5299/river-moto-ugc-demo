"""Data models for avatar/talking-head generation requests and results."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel


class AvatarRequest(BaseModel):
    """Request for talking-head video generation.

    Single-pass backends (fal.ai ai-avatar): provide image_path + text + voice.
    Two-pass backends (Sync Labs): provide image_path + audio_path.
    """

    image_path: Path
    text: str | None = None  # Script text (single-pass backends do TTS internally)
    voice: str = "Bill"  # Voice name for single-pass TTS
    audio_path: Path | None = None  # Pre-generated audio (two-pass backends)
    prompt: str | None = None  # Visual guidance prompt
    resolution: str = "720p"  # "480p" or "720p"
    num_frames: int | None = None  # None = use backend default
    output_path: Path | None = None
    model: str | None = None  # Backend-specific model override

    # HeyGen mode:
    #   "talking_photo"  — v1, face/lips only, cheap
    #   "avatar_iv"      — Photo Avatar IV (/v2/video/av4/generate), head+body motion
    #   "video_agent"    — Seedance 2.0 (/v1/video_agent/generate), cinematic scene
    #                      generation with optional avatar composite; 4 credits/sec
    heygen_mode: str = "talking_photo"

    # Avatar IV only — describes the gestures / body language / facial expressions
    # the model should weave in. Built per-video by the pipeline from the script
    # context + scenario tags (e.g. "subtle smirk, confident posture, hands relaxed").
    # Optional — HeyGen falls back to defaults if empty.
    custom_motion_prompt: str = ""

    # Video Agent only — HeyGen registered photo-avatar ID to composite into
    # the scene. Locks character identity across the generation in a way a
    # reference image alone does not (Seedance treats images as style hints
    # and drifts faces over 5-15s clips). Look up per character in
    # configs/heygen_photo_ids.json. When set, passed as config.avatar_id in
    # the /v1/video_agent/generate payload.
    avatar_id: str | None = None


class AvatarResult(BaseModel):
    """Result from avatar/talking-head generation."""

    video_path: Path
    duration_sec: float
    width: int
    height: int
    generation_time_sec: float
