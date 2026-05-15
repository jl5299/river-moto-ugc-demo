# HeyGen Render Path

The public Revenants slice demonstrates the image-to-video render path used by
the private pipeline:

1. Start with one or more structured shot dictionaries.
2. Convert each shot into a concise reference-video prompt.
3. Send the prompt plus a keyframe to Olympus' HeyGen backend.
4. Retry known transient HeyGen/Seedance failures.
5. Return normalized `ShotResult` objects with output paths, dimensions,
   duration, and estimated cost.

The central call is:

```python
from revenants.render import render_scene_shots_heygen

results = render_scene_shots_heygen(
    shots=shots,
    keyframes=[Path("keyframe.png") for _ in shots],
    output_dir=Path("outputs/heygen-demo/demo1"),
)
```

`HEYGEN_API_KEY` is read from the environment by the Olympus backend.
