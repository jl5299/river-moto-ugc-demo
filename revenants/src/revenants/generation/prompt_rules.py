"""Prompt helpers for reference-image video generation.

HeyGen Video Agent receives both a keyframe and a text prompt. The keyframe
already carries identity, wardrobe, and composition, so the text prompt should
continue motion from that frame instead of reintroducing the subject.
"""

from __future__ import annotations

import re
from typing import Any


REFERENCE_VIDEO_RESTART_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (
        re.compile(
            r"\b(?:same|the same)\s+(?:person|character|man|woman|subject)\b"
            r"[^.!?\n]{0,90}\b(?:reference image|throughout|frame)\b",
            re.IGNORECASE,
        ),
        "reference-video prompt reintroduces the character instead of continuing the frame",
    ),
    (
        re.compile(
            r"\b(?:preserve|maintain|keep|keeping)\b[^.!?\n]{0,90}"
            r"\b(?:identity|facial features|face|body|appearance)\b",
            re.IGNORECASE,
        ),
        "reference-video prompt restates identity; the keyframe already carries identity",
    ),
    (
        re.compile(r"(?:^|\s)Outfit:\s*[^.!?\n]+[.!?]?", re.IGNORECASE),
        "wardrobe belongs in the keyframe, not the motion prompt",
    ),
    (
        re.compile(r"(?:^|\s)Framing:\s*[^.!?\n]+[.!?]?", re.IGNORECASE),
        "camera framing belongs in the composed scene prompt",
    ),
)


def strip_reference_video_restart_cues(text: str) -> str:
    """Remove restart cues that can make image-to-video models recast a subject."""

    value = text or ""
    for pattern, _label in REFERENCE_VIDEO_RESTART_PATTERNS:
        value = pattern.sub(" ", value)
    value = re.sub(r"\s{2,}", " ", value)
    value = re.sub(r"\s+([,.!?])", r"\1", value)
    value = re.sub(r"([.!?]){2,}", r"\1", value)
    return value.strip()


def build_reference_video_prompt(
    shot: dict[str, Any],
    *,
    fallback: str = "Cinematic portrait moment.",
) -> str:
    """Return the HeyGen/Seedance prompt for one reference-image shot.

    The preferred source is ``shot["scene_description"]``. The public demo
    also accepts structured pieces so it can be run by hand without the full
    private artifact pipeline.
    """

    scene_desc = str((shot or {}).get("scene_description") or "").strip()
    if not scene_desc:
        pieces = [
            shot.get("setting"),
            shot.get("action"),
            shot.get("dialogue") and f'Spoken line: "{shot["dialogue"]}"',
            shot.get("camera"),
            shot.get("lighting"),
            shot.get("constraints"),
        ]
        scene_desc = ". ".join(str(piece).strip().rstrip(".") for piece in pieces if piece)
        if scene_desc:
            scene_desc += "."
    return strip_reference_video_restart_cues(scene_desc) or fallback
