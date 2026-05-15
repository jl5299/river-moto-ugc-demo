# River Moto UGC Studio

Public HeyGen hackathon demo showing a seeded motorcycle UGC pipeline.

This repo includes:

- `olympus/` — public-safe HeyGen Video Agent backend slice
- `revenants/` — prompt and multi-shot render orchestration slice
- `src/` — deployable web demo seeded with fake `demo1`, `demo2`, `demo3` accounts

The demo intentionally uses fake creators and a fictional motorcycle company.
Private account automation, platform credentials, production queues, and real
brand configs are excluded.

## Web Demo

```bash
npm install
npm run dev
```

## HeyGen Render Demo

```bash
cd revenants
python -m pip install -e ../olympus
python -m pip install -e .
HEYGEN_API_KEY=... python examples/heygen_video_agent_demo.py \
  --demo-user demo1 \
  --keyframe ../public/personas/demo1.png
```

Rendered files are written to `revenants/outputs/` and ignored by git.
