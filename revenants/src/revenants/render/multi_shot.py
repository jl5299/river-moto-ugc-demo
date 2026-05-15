"""HeyGen Video Agent multi-shot renderer.

This is the public-safe Revenants render path adapted from the private
pipeline. Revenants owns shot orchestration, prompt cleanup, retry behavior,
checkpoint metadata, and normalized results. Olympus owns the HeyGen API
backend used to submit and poll jobs.
"""

from __future__ import annotations

import os
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from revenants.generation.prompt_rules import build_reference_video_prompt

try:
    from olympus.hermes.logging import get_logger
except Exception:  # pragma: no cover - public demo can run before Olympus is installed.
    import logging

    def get_logger(name: str) -> logging.Logger:
        return logging.getLogger(name)


log = get_logger(__name__)

# HeyGen Video Agent pricing at time of extraction:
# 4 credits/sec, $24 / 4000 credits = $0.006/credit.
HEYGEN_VIDEO_AGENT_USD_PER_SECOND = 4 * (24 / 4000)
MAX_HEYGEN_RETRIES = 3


@dataclass
class ShotResult:
    """One rendered video shot."""

    shot_index: int
    video_path: Path
    duration_sec: float
    width: int
    height: int
    photo_path: Path
    credits_used: float
    usd_cost: float


def _probe_existing_video(raw_path: Path, fallback_duration: int) -> tuple[float, int, int]:
    try:
        from olympus.forge.avatar.heygen import _probe_video

        duration_sec, width, height = _probe_video(raw_path)
        return float(duration_sec), int(width), int(height)
    except Exception:
        return float(fallback_duration), 1080, 1920


def _is_retryable_heygen_error(message: str) -> bool:
    return (
        "MOVIO_VIDEO_TOO_SHORT" in message
        or "Text cannot be empty" in message
        or "VOICE_PROVIDER_ERROR" in message
    )


def render_scene_shots_heygen(
    *,
    shots: list[dict],
    keyframes: list[Path],
    output_dir: Path,
    duration_per_shot_s: int = 5,
    shot_raw_paths: list[Path] | None = None,
    resume_state: list[dict] | None = None,
    state_writer: Callable[[int, dict], None] | None = None,
    avatar_id: str | None = None,
) -> list[ShotResult]:
    """Render every shot in a scene via HeyGen Video Agent.

    Each shot becomes one HeyGen ``/v1/video_agent/generate`` call using the
    keyframe as the visual reference and the shot prompt as motion/dialogue
    direction. Resume metadata lets callers skip already-rendered shots after a
    timeout or failed later shot.
    """

    from olympus.forge.avatar._models import AvatarRequest
    from olympus.forge.avatar.heygen import HeyGenAvatarBackend

    if len(shots) != len(keyframes):
        raise ValueError(
            f"shot/keyframe count mismatch: {len(shots)} shots vs {len(keyframes)} keyframes"
        )
    if shot_raw_paths is not None and len(shot_raw_paths) != len(shots):
        raise ValueError(
            f"shot_raw_paths length mismatch: {len(shot_raw_paths)} vs {len(shots)} shots"
        )

    api_key = os.environ.get("HEYGEN_API_KEY", "")
    if not api_key:
        raise RuntimeError("render_scene_shots_heygen requires HEYGEN_API_KEY")

    output_dir.mkdir(parents=True, exist_ok=True)
    backend = HeyGenAvatarBackend(api_key=api_key)
    results: list[ShotResult] = []

    for i, (shot, keyframe_path) in enumerate(zip(shots, keyframes)):
        shot_duration = int(shot.get("duration_s") or duration_per_shot_s)
        dest_path = (
            shot_raw_paths[i]
            if shot_raw_paths is not None
            else output_dir / f"shot_{i + 1:02d}.mp4"
        )
        dest_path.parent.mkdir(parents=True, exist_ok=True)

        prior = (resume_state[i] if resume_state and i < len(resume_state) else None) or {}
        prior_raw = prior.get("raw_path")
        if prior.get("status") == "done" and prior_raw and Path(prior_raw).exists():
            raw_path = Path(prior_raw)
            duration_sec = float(prior.get("duration_sec") or 0.0)
            width = int(prior.get("width") or 0)
            height = int(prior.get("height") or 0)
            if not (duration_sec and width and height):
                duration_sec, width, height = _probe_existing_video(raw_path, shot_duration)
            usd = float(prior.get("usd_cost") or 0.0)
            results.append(
                ShotResult(
                    shot_index=i,
                    video_path=raw_path,
                    duration_sec=duration_sec,
                    width=width,
                    height=height,
                    photo_path=keyframe_path,
                    credits_used=shot_duration * 4,
                    usd_cost=usd,
                )
            )
            if state_writer is not None:
                state_writer(i, {**prior, "status": "done", "raw_path": str(raw_path)})
            log.info("heygen_shot_resumed", shot=i + 1, path=str(raw_path))
            continue

        prompt = build_reference_video_prompt(shot)
        request = AvatarRequest(
            image_path=keyframe_path,
            prompt=prompt,
            output_path=dest_path,
            heygen_mode="video_agent",
            num_frames=shot_duration,
            avatar_id=avatar_id,
        )

        log.info(
            "heygen_shot_begin",
            shot=i + 1,
            of=len(shots),
            keyframe=keyframe_path.name,
            duration=shot_duration,
            dest=str(dest_path),
        )

        result = None
        last_exc: Exception | None = None
        for attempt in range(MAX_HEYGEN_RETRIES):
            try:
                result = backend._generate_video_agent_sync(request)
                last_exc = None
                break
            except Exception as exc:
                last_exc = exc
                msg = str(exc)
                if _is_retryable_heygen_error(msg) and attempt + 1 < MAX_HEYGEN_RETRIES:
                    log.warning(
                        "heygen_transient_retry",
                        shot=i + 1,
                        attempt=attempt + 1,
                        of=MAX_HEYGEN_RETRIES,
                        error=msg[:180],
                    )
                    continue
                if state_writer is not None:
                    state_writer(i, {"index": i, "status": "failed", "error": msg[:500]})
                raise

        if result is None:
            raise last_exc or RuntimeError("HeyGen shot rendering failed with no result")

        usd = shot_duration * HEYGEN_VIDEO_AGENT_USD_PER_SECOND
        results.append(
            ShotResult(
                shot_index=i,
                video_path=result.video_path,
                duration_sec=result.duration_sec,
                width=result.width,
                height=result.height,
                photo_path=keyframe_path,
                credits_used=shot_duration * 4,
                usd_cost=usd,
            )
        )
        if state_writer is not None:
            state_writer(
                i,
                {
                    "index": i,
                    "status": "done",
                    "backend": "heygen",
                    "raw_path": str(result.video_path),
                    "width": result.width,
                    "height": result.height,
                    "duration_sec": result.duration_sec,
                    "usd_cost": round(usd, 4),
                },
            )
        log.info(
            "heygen_shot_done",
            shot=i + 1,
            duration=f"{result.duration_sec:.1f}s",
            usd=f"${usd:.3f}",
        )

    log.info(
        "heygen_multi_shot_complete",
        shots=len(results),
        total_usd=sum(r.usd_cost for r in results),
    )
    return results
