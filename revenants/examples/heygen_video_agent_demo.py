"""Render a short multi-shot vertical video with HeyGen Video Agent.

This example uses the Revenants shot contract and the Olympus HeyGen backend.
Run it from this directory after installing the sibling public Olympus copy:

    python examples/heygen_video_agent_demo.py --keyframe ./examples/keyframe.png

The script expects HEYGEN_API_KEY in the environment. It writes one MP4 per
shot under outputs/heygen-demo/.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from dotenv import load_dotenv

from revenants.render import render_scene_shots_heygen


DEMO_USERS_PATH = Path(__file__).with_name("demo_users.json")


def _load_demo_users() -> list[dict]:
    return json.loads(DEMO_USERS_PATH.read_text())


def _select_demo_user(user_id: str) -> dict:
    users = _load_demo_users()
    for user in users:
        if user["id"] == user_id:
            return user
    valid = ", ".join(user["id"] for user in users)
    raise SystemExit(f"unknown demo user {user_id!r}; choose one of: {valid}")


def _demo_shots(user: dict) -> list[dict]:
    handle = user["handle"]
    niche = user["niche"]
    offer = user["offer"]
    return [
        {
            "duration_s": 5,
            "shot_style": "talking_head",
            "framing": "vertical phone video, medium close-up",
            "setting": "bright workshop desk with a laptop and small camera light",
            "action": (
                f"{handle} leans in, gestures to a timeline on the laptop, "
                f"then smiles while introducing a {niche} clip"
            ),
            "dialogue": f"Today I am turning one idea into a finished {niche} short.",
            "camera": "handheld phone camera, subtle push-in, natural motion",
            "lighting": "soft daylight from the side, realistic skin texture",
            "constraints": "no subtitles, no logos, no extra people",
        },
        {
            "duration_s": 5,
            "shot_style": "talking_head",
            "framing": "vertical phone video, medium close-up",
            "setting": "same workshop desk, laptop now showing a video preview",
            "action": f"{handle} taps play on the preview and points at the rendered result",
            "dialogue": f"HeyGen handles the motion and delivery, so I can focus on {offer}.",
            "camera": "gentle handheld sway, realistic creator-shot footage",
            "lighting": "same soft daylight, consistent face and outfit",
            "constraints": "no subtitles, no logos, no extra people",
        },
    ]


def main() -> None:
    load_dotenv()

    parser = argparse.ArgumentParser()
    parser.add_argument("--keyframe", type=Path, help="Reference image for the subject")
    parser.add_argument("--demo-user", default="demo1", help="Fake user id from examples/demo_users.json")
    parser.add_argument("--out", default=Path("outputs/heygen-demo"), type=Path)
    parser.add_argument("--avatar-id", default="", help="Optional HeyGen avatar_id for stronger identity lock")
    parser.add_argument("--list-users", action="store_true", help="Print fake demo users and exit")
    args = parser.parse_args()

    if args.list_users:
        for user in _load_demo_users():
            print(f"{user['id']}: {user['handle']} — {user['niche']}")
        return

    if not os.environ.get("HEYGEN_API_KEY"):
        raise SystemExit("HEYGEN_API_KEY is required")
    if args.keyframe is None:
        raise SystemExit("--keyframe is required unless --list-users is used")
    if not args.keyframe.exists():
        raise SystemExit(f"keyframe not found: {args.keyframe}")

    user = _select_demo_user(args.demo_user)
    shots = _demo_shots(user)
    results = render_scene_shots_heygen(
        shots=shots,
        keyframes=[args.keyframe for _ in shots],
        output_dir=args.out / user["id"],
        avatar_id=args.avatar_id or None,
    )

    print(f"rendered for {user['id']} ({user['handle']})")
    for result in results:
        print(f"shot {result.shot_index + 1}: {result.video_path} (${result.usd_cost:.3f})")


if __name__ == "__main__":
    main()
