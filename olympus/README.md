# Olympus HeyGen Demo Slice

This package is the public-safe Olympus side of the hackathon repo. It keeps
only the `olympus.forge.avatar.heygen` backend plus the request/result models
needed by Revenants.

The backend supports HeyGen Video Agent through:

```python
from olympus.forge.avatar import AvatarRequest, HeyGenAvatarBackend

backend = HeyGenAvatarBackend(api_key="...")
result = backend._generate_video_agent_sync(
    AvatarRequest(
        image_path="keyframe.png",
        prompt="Vertical creator footage, subject explains the product.",
        output_path="outputs/shot.mp4",
        heygen_mode="video_agent",
        num_frames=5,
    )
)
```

No private Olympus services, cron scripts, data exports, or credentials are
included.
