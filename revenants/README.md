# Revenants HeyGen Demo Slice

This is the public-safe Revenants side of the HeyGen hackathon copy. It is
based on `jl5299/revenants` branch `origin/refactor-by-dataflow` at commit
`96aa79e` and keeps the pieces that matter for generated vertical video:

- `revenants.render.multi_shot.render_scene_shots_heygen`
- `revenants.generation.prompt_rules.build_reference_video_prompt`
- the shared `ShotResult` contract used by the render path
- a small runnable HeyGen Video Agent example

Private account automation, platform credentials, Android device ops, crons,
database migrations, and brand/private configs are intentionally excluded.

## Setup

Install the sibling public Olympus copy first, because the HeyGen backend lives
there:

```bash
python -m pip install -e ../olympus
python -m pip install -e .
cp .env.example .env
```

Then set `HEYGEN_API_KEY` in your shell or `.env`.

## Run The HeyGen Demo

Provide a portrait reference image:

```bash
python examples/heygen_video_agent_demo.py --list-users
HEYGEN_API_KEY=... python examples/heygen_video_agent_demo.py \
  --demo-user demo1 \
  --keyframe ./examples/keyframe.png
```

The example creates two HeyGen Video Agent shots in `outputs/heygen-demo/demo1/`.
Each shot sends a keyframe plus a structured motion/dialogue prompt to the
HeyGen Video Agent path.

The fake roster lives at `examples/demo_users.json`; it intentionally uses
`demo1`, `demo2`, `demo3`, etc. instead of private customer or brand names.

## What Revenants Adds

Revenants is the orchestration layer: it turns structured shot metadata into
model-safe video prompts, tracks per-shot costs, retries known transient
HeyGen/Seedance failures, and returns normalized `ShotResult` objects for
downstream stitching or review.
