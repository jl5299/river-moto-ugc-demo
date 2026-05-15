"""HeyGen avatar backend — talking head with custom backgrounds.

Single API call: photo avatar + text/audio + background image → video.
Supports transparent output, green screen, custom background images, 9:16 native.

Requires: HEYGEN_API_KEY env var.
Docs: https://docs.heygen.com
"""

from __future__ import annotations

import asyncio
import json
import os
import subprocess
import tempfile
import time
from pathlib import Path

import httpx
from olympus.hermes.logging import get_logger
from olympus.forge.avatar._models import AvatarRequest, AvatarResult

log = get_logger(__name__)

API_BASE = "https://api.heygen.com"
UPLOAD_BASE = "https://upload.heygen.com"
POLL_INTERVAL_SEC = 5
# 25min per-shot ceiling. Aligned with render_worker.sh REAPER (30min
# total-render cutoff) — we want HeyGen's TimeoutError to fire first so
# the subprocess exits cleanly with a useful error BEFORE the REAPER
# orphans the row. Typical HeyGen shot: 30s-5min. p99 tail: ~10min.
# 25min means "this API call is definitively stuck" — raising below
# the REAPER cutoff gives clean diagnostic info rather than a silent
# subprocess kill.
MAX_POLL_SEC = 1500


class HeyGenAvatarBackend:
    """Talking head video via HeyGen: photo avatar + text + background → video.

    Supports:
    - Custom background images (no post-processing needed)
    - Green screen output (chroma key)
    - Built-in TTS with emotion control
    - 9:16 vertical (1080x1920) native
    - Up to 30 min video (no stitching for shorts)
    """

    def __init__(self, api_key: str | None = None) -> None:
        self._api_key = api_key or os.environ.get("HEYGEN_API_KEY", "")
        self._headers = {
            "x-api-key": self._api_key,
            "Content-Type": "application/json",
        }

    @property
    def is_loaded(self) -> bool:
        return True

    @property
    def vram_estimate_mb(self) -> int:
        return 0

    async def load_model(self) -> None:
        pass

    async def unload_model(self) -> None:
        pass

    async def generate(self, request: AvatarRequest) -> AvatarResult:
        loop = asyncio.get_event_loop()
        mode = request.heygen_mode or "talking_photo"
        if mode == "video_agent":
            return await loop.run_in_executor(None, self._generate_video_agent_sync, request)
        if mode == "avatar_iv":
            return await loop.run_in_executor(None, self._generate_avatar_iv_sync, request)
        return await loop.run_in_executor(None, self._generate_sync, request)

    # ── Public helpers ───────────────────────────────────────

    def upload_talking_photo(self, image_path: Path) -> str:
        """Upload an image and get a talking_photo_id for reuse.

        Uses the legacy endpoint which returns an ID immediately. The resulting
        photo_id only animates the face/lips when used with the v1 talking_photo
        character mode — the body stays static. For natural body motion, use
        upload_image_for_avatar_iv() instead.
        """
        content_type = "image/png" if image_path.suffix == ".png" else "image/jpeg"
        with httpx.Client(timeout=60) as client:
            with open(image_path, "rb") as f:
                resp = client.post(
                    f"{UPLOAD_BASE}/v1/talking_photo",
                    headers={
                        "x-api-key": self._api_key,
                        "Content-Type": content_type,
                    },
                    content=f.read(),
                )
                resp.raise_for_status()
                data = resp.json()
                photo_id = data["data"]["talking_photo_id"]
                log.info("heygen_photo_uploaded", talking_photo_id=photo_id)
                return photo_id

    def upload_image_for_avatar_iv(self, image_path: Path) -> str:
        """Upload an image and return an `image_key` for HeyGen Photo Avatar IV.

        Avatar IV is HeyGen's newer animation model that produces natural head,
        shoulder, and upper-body motion from a single still photo (talking_photo
        only animates lips). Costs ~2x credits per video but is dramatically
        more lifelike.

        Uses the same `/v1/asset` endpoint as upload_asset() but returns an
        image_key in the format `image/{asset_id}/original` that the v2 video
        generate endpoint understands as character.type=image input.
        """
        suffix = image_path.suffix.lower()
        content_types = {
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
        }
        content_type = content_types.get(suffix, "image/jpeg")
        with httpx.Client(timeout=60) as client:
            with open(image_path, "rb") as f:
                resp = client.post(
                    f"{UPLOAD_BASE}/v1/asset",
                    headers={
                        "x-api-key": self._api_key,
                        "Content-Type": content_type,
                    },
                    content=f.read(),
                )
                resp.raise_for_status()
                data = resp.json()
                # Asset upload returns {"data": {"id": "...", "image_key": "...", "url": ...}}
                # Prefer image_key if present, otherwise build it from id.
                d = data.get("data", {})
                image_key = d.get("image_key") or f"image/{d['id']}/original"
                log.info("heygen_image_uploaded_for_avatar_iv", image_key=image_key)
                return image_key

    def upload_asset(self, file_path: Path) -> str:
        """Upload an image/audio/video asset and get an asset_id."""
        suffix = file_path.suffix.lower()
        content_types = {
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".mp3": "audio/mpeg",
            ".wav": "audio/wav",
            ".mp4": "video/mp4",
        }
        content_type = content_types.get(suffix, "application/octet-stream")

        with httpx.Client(timeout=60) as client:
            with open(file_path, "rb") as f:
                resp = client.post(
                    f"{UPLOAD_BASE}/v1/asset",
                    headers={
                        "x-api-key": self._api_key,
                        "Content-Type": content_type,
                    },
                    content=f.read(),
                )
                resp.raise_for_status()
                data = resp.json()
                asset_id = data["data"]["id"]
                log.info("heygen_asset_uploaded", asset_id=asset_id, type=content_type)
                return asset_id

    def list_voices(self) -> list[dict]:
        """List available TTS voices."""
        with httpx.Client(timeout=30) as client:
            resp = client.get(
                f"{API_BASE}/v2/voices",
                headers=self._headers,
            )
            resp.raise_for_status()
            return resp.json()["data"]["voices"]

    def list_avatars(self) -> dict:
        """List available avatars and talking photos."""
        with httpx.Client(timeout=30) as client:
            resp = client.get(
                f"{API_BASE}/v2/avatars",
                headers=self._headers,
            )
            resp.raise_for_status()
            return resp.json()["data"]

    # ── Core generation ──────────────────────────────────────

    def _generate_sync(self, request: AvatarRequest) -> AvatarResult:
        start = time.monotonic()

        if not request.text and not request.audio_path:
            raise ValueError("HeyGen requires either text or audio_path.")

        # ── Build character config based on heygen_mode ──
        # "avatar_iv": newer Photo Avatar IV — animates head + shoulders + upper
        #   body from a single still. character.type="image", uses image_key.
        # "talking_photo" (default): legacy v1 — face/lips only animation, body
        #   static. character.type="talking_photo", uses talking_photo_id.
        #
        # image_path is dual-purpose:
        #   - starts with "image/" → cached image_key from a previous Avatar IV
        #     upload (note: HeyGen image_keys end with .jpg/.original, so the
        #     prefix check MUST come BEFORE the suffix check below)
        #   - extensionless and not "image/" → legacy talking_photo_id
        #   - real file path → upload, route based on request.heygen_mode
        mode = request.heygen_mode or "talking_photo"
        path_str = str(request.image_path)

        if path_str.startswith("image/"):
            # Cached image_key from a previous Avatar IV upload
            image_key = path_str
            talking_photo_id = None
            mode = "avatar_iv"
        elif request.image_path.suffix == "":
            # Extensionless string = legacy talking_photo_id
            talking_photo_id = path_str
            image_key = None
            mode = "talking_photo"
        else:
            # Real file path — upload according to chosen mode
            if mode == "avatar_iv":
                image_key = self.upload_image_for_avatar_iv(request.image_path)
                talking_photo_id = None
            else:
                talking_photo_id = self.upload_talking_photo(request.image_path)
                image_key = None

        if mode == "avatar_iv":
            character = {
                "type": "image",
                "image_key": image_key,
                "avatar_style": "normal",
            }
        else:
            character = {
                "type": "talking_photo",
                "talking_photo_id": talking_photo_id,
                "talking_style": "expressive",
                "expression": "happy",
                "matting": False,
            }

        # Build voice config
        if request.text:
            voice = {
                "type": "text",
                "voice_id": request.voice,
                "input_text": request.text,
                "speed": 1.0,
            }
        else:
            # Convert to MP3 if needed (HeyGen prefers MP3 for audio assets)
            audio_path = request.audio_path
            if audio_path.suffix.lower() == ".wav":
                mp3_path = audio_path.with_suffix(".mp3")
                subprocess.run(
                    ["python3", "-c", f"""
from moviepy import AudioFileClip
clip = AudioFileClip("{audio_path}")
clip.write_audiofile("{mp3_path}", logger=None)
clip.close()
"""],
                    check=True, capture_output=True,
                )
                audio_path = mp3_path
                log.info("heygen_converted_wav_to_mp3", path=str(mp3_path))

            audio_asset_id = self.upload_asset(audio_path)
            voice = {
                "type": "audio",
                "audio_asset_id": audio_asset_id,
            }

        # Build background config
        background = self._build_background(request)

        # Build the full request
        payload = {
            "dimension": {"width": 1080, "height": 1920},
            "video_inputs": [
                {
                    "character": character,
                    "voice": voice,
                    "background": background,
                }
            ],
        }

        log.info(
            "heygen_generating",
            mode=mode,
            talking_photo_id=talking_photo_id,
            image_key=image_key,
            has_text=bool(request.text),
            background_type=background.get("type"),
        )

        with httpx.Client(timeout=300) as client:
            # Submit video generation
            resp = client.post(
                f"{API_BASE}/v2/video/generate",
                headers=self._headers,
                json=payload,
            )
            if resp.status_code >= 400:
                # Capture HeyGen's error body before raise_for_status throws it away
                log.error(
                    "heygen_v2_generate_http_error",
                    status=resp.status_code,
                    body=resp.text[:1000],
                    payload=json.dumps(payload)[:500],
                )
            resp.raise_for_status()
            resp_data = resp.json()

            if resp_data.get("error"):
                raise RuntimeError(f"HeyGen error: {resp_data['error']}")

            video_id = resp_data["data"]["video_id"]
            log.info("heygen_job_created", video_id=video_id)

            # Poll for completion
            video_url = self._poll_for_completion(client, video_id)

            # Download result
            if request.output_path:
                output_path = Path(request.output_path)
                output_path.parent.mkdir(parents=True, exist_ok=True)
            else:
                output_path = Path(tempfile.mktemp(suffix=".mp4"))

            log.info("heygen_downloading")
            dl_resp = client.get(video_url, follow_redirects=True)
            dl_resp.raise_for_status()
            output_path.write_bytes(dl_resp.content)

        # Probe video metadata
        duration_sec, width, height = _probe_video(output_path)

        elapsed = time.monotonic() - start
        log.info(
            "heygen_generated",
            duration=f"{duration_sec:.1f}s",
            resolution=f"{width}x{height}",
            elapsed=f"{elapsed:.1f}s",
            path=str(output_path),
        )

        return AvatarResult(
            video_path=output_path,
            duration_sec=duration_sec,
            width=width,
            height=height,
            generation_time_sec=elapsed,
        )

    def _generate_avatar_iv_sync(self, request: AvatarRequest) -> AvatarResult:
        """Generate a video via HeyGen Photo Avatar IV (POST /v2/video/av4/generate).

        Avatar IV is a separate endpoint from /v2/video/generate. It produces
        natural head + shoulder + upper-body motion from a single still photo.
        Voice can come from EITHER:
          1. HeyGen TTS — pass request.text + request.voice (voice_id)
          2. Pre-generated audio — pass request.audio_path (we upload via
             /v1/asset and pass audio_asset_id, preserving ElevenLabs voices)

        Required:
          - request.image_path: file path to upload OR cached image_key string
        """
        start = time.monotonic()

        if not request.text and not request.audio_path:
            raise ValueError(
                "Avatar IV requires either request.text+voice or request.audio_path."
            )

        path_str = str(request.image_path)
        if path_str.startswith("image/"):
            image_key = path_str
        else:
            image_key = self.upload_image_for_avatar_iv(request.image_path)

        payload: dict = {
            "image_key": image_key,
            "video_title": "river-moto-demo",
            "dimension": {"width": 720, "height": 1280},
        }
        # Optional motion prompt — drives gestures / body language / expressions.
        # When set, also tell HeyGen's LLM to enhance/refine it for fidelity.
        if request.custom_motion_prompt:
            payload["custom_motion_prompt"] = request.custom_motion_prompt
            payload["enhance_custom_motion_prompt"] = True

        # Voice source — pre-generated audio takes priority over TTS
        if request.audio_path:
            audio_path = request.audio_path
            if audio_path.suffix.lower() == ".wav":
                # HeyGen prefers MP3 — convert
                mp3_path = audio_path.with_suffix(".mp3")
                subprocess.run(
                    ["python3", "-c", f"""
from moviepy import AudioFileClip
clip = AudioFileClip("{audio_path}")
clip.write_audiofile("{mp3_path}", logger=None)
clip.close()
"""],
                    check=True, capture_output=True,
                )
                audio_path = mp3_path
            audio_asset_id = self.upload_asset(audio_path)
            payload["audio_asset_id"] = audio_asset_id
        else:
            # HeyGen built-in TTS path
            heygen_voice_map = {
                "Roger": "24d7bea6d62143cc8fa0178a9c1ec5b7",
                "Daniel": "0c23804af39a4946ac6fda42bfff2738",
                "Charlie": "2eaac9d267b34cacbc78df758a836966",
                "Bill": "aacfeef94f5644dd94943080cd3c6f09",
            }
            voice_id = heygen_voice_map.get(request.voice, request.voice)
            payload["script"] = request.text
            payload["voice_id"] = voice_id

        log.info(
            "heygen_av4_generating",
            image_key=image_key,
            has_audio_asset="audio_asset_id" in payload,
            has_script="script" in payload,
        )

        with httpx.Client(timeout=300) as client:
            resp = client.post(
                f"{API_BASE}/v2/video/av4/generate",
                headers=self._headers,
                json=payload,
            )
            if resp.status_code >= 400:
                log.error(
                    "heygen_av4_http_error",
                    status=resp.status_code,
                    body=resp.text[:1000],
                    payload=json.dumps(payload)[:500],
                )
            resp.raise_for_status()
            resp_data = resp.json()

            if resp_data.get("error"):
                raise RuntimeError(f"HeyGen av4 error: {resp_data['error']}")

            video_id = resp_data["data"]["video_id"]
            log.info("heygen_av4_job_created", video_id=video_id)

            video_url = self._poll_for_completion(client, video_id)

            if request.output_path:
                output_path = Path(request.output_path)
                output_path.parent.mkdir(parents=True, exist_ok=True)
            else:
                output_path = Path(tempfile.mktemp(suffix=".mp4"))

            log.info("heygen_av4_downloading")
            with client.stream("GET", video_url) as r:
                r.raise_for_status()
                with open(output_path, "wb") as f:
                    for chunk in r.iter_bytes(chunk_size=1024 * 64):
                        f.write(chunk)

        duration_sec, width, height = _probe_video(output_path)
        elapsed = time.monotonic() - start
        log.info(
            "heygen_av4_generated",
            duration=f"{duration_sec:.1f}s",
            resolution=f"{width}x{height}",
            elapsed=f"{elapsed:.1f}s",
            path=str(output_path),
        )

        return AvatarResult(
            video_path=output_path,
            duration_sec=duration_sec,
            width=width,
            height=height,
            generation_time_sec=elapsed,
        )

    def _build_background(self, request: AvatarRequest) -> dict:
        """Build background config from request.

        The prompt field is overloaded for background control:
        - "transparent" → transparent WebM
        - "green_screen" → green color background
        - "#RRGGBB" → solid color
        - Path to image file → upload and use as background
        - URL starting with http → use as background URL
        - Anything else → default dark background
        """
        prompt = (request.prompt or "").strip()

        if prompt == "transparent":
            return {"type": "transparent"}
        elif prompt == "green_screen":
            return {"type": "color", "value": "#008000"}
        elif prompt.startswith("#") and len(prompt) == 7:
            return {"type": "color", "value": prompt}
        elif prompt.startswith("http"):
            return {"type": "image", "url": prompt, "fit": "cover"}
        elif prompt and Path(prompt).exists():
            asset_id = self.upload_asset(Path(prompt))
            return {"type": "image", "image_asset_id": asset_id, "fit": "cover"}
        else:
            # Default: dark background that looks good for shorts
            return {"type": "color", "value": "#0a0a0a"}

    def _generate_video_agent_sync(self, request: AvatarRequest) -> AvatarResult:
        """Generate via HeyGen Video Agent — Seedance 2.0 powered.

        POST /v1/video_agent/generate
        - prompt drives the cinematic scene (Seedance 2.0 underneath)
        - files[].asset_id passes a reference image (our Flux keyframe)
        - config.avatar_id places a HeyGen avatar in the scene (optional)
        - Pricing: 4 credits/sec → ~48 credits for 12s
        - Orientation: portrait (9:16)

        request fields used:
          image_path  → uploaded as asset → passed in files[] for visual reference
          text        → used as the scene prompt (visual_premise + context)
          prompt      → if set, used verbatim; otherwise built from text
          custom_motion_prompt → appended to scene prompt for motion guidance
          output_path → where to write the downloaded mp4
        """
        start = time.monotonic()

        # Build the scene prompt — prompt field wins, otherwise use text
        scene_prompt = (request.prompt or request.text or "").strip()
        if request.custom_motion_prompt:
            scene_prompt = f"{scene_prompt} {request.custom_motion_prompt}".strip()
        if not scene_prompt:
            raise ValueError("video_agent requires either request.prompt or request.text")

        payload: dict = {
            "prompt": scene_prompt,
            "config": {
                "duration_sec": request.num_frames or 5,
                "orientation": "portrait",
            },
        }

        # Optional avatar_id (HeyGen avatar to composite into the scene)
        if request.avatar_id:
            payload["config"]["avatar_id"] = request.avatar_id
        elif request.voice and not request.voice.startswith("image/"):
            # reuse voice field as avatar_id when it looks like a HeyGen avatar ID
            if len(request.voice) > 20 and "_" in request.voice:
                payload["config"]["avatar_id"] = request.voice

        # Upload Flux keyframe as reference image
        files = []
        if request.image_path and Path(str(request.image_path)).exists():
            asset_id = self.upload_asset(request.image_path)
            files.append({"asset_id": asset_id})
        if files:
            payload["files"] = files

        log.info(
            "heygen_video_agent_generating",
            prompt_snippet=scene_prompt[:80],
            has_reference_image=bool(files),
            has_avatar=bool(payload["config"].get("avatar_id")),
        )

        with httpx.Client(timeout=300) as client:
            resp = client.post(
                f"{API_BASE}/v1/video_agent/generate",
                headers=self._headers,
                json=payload,
            )
            if resp.status_code >= 400:
                log.error(
                    "heygen_video_agent_http_error",
                    status=resp.status_code,
                    body=resp.text[:1000],
                )
            resp.raise_for_status()
            resp_data = resp.json()

            if resp_data.get("error"):
                raise RuntimeError(f"HeyGen video_agent error: {resp_data['error']}")

            video_id = resp_data["data"]["video_id"]
            log.info("heygen_video_agent_job_created", video_id=video_id)

            video_url = self._poll_for_completion(client, video_id)

            if request.output_path:
                output_path = Path(request.output_path)
                output_path.parent.mkdir(parents=True, exist_ok=True)
            else:
                output_path = Path(tempfile.mktemp(suffix=".mp4"))

            log.info("heygen_video_agent_downloading")
            with client.stream("GET", video_url) as r:
                r.raise_for_status()
                with open(output_path, "wb") as f:
                    for chunk in r.iter_bytes(chunk_size=1024 * 64):
                        f.write(chunk)

        duration_sec, width, height = _probe_video(output_path)
        elapsed = time.monotonic() - start
        log.info(
            "heygen_video_agent_generated",
            duration=f"{duration_sec:.1f}s",
            resolution=f"{width}x{height}",
            elapsed=f"{elapsed:.1f}s",
            path=str(output_path),
        )

        return AvatarResult(
            video_path=output_path,
            duration_sec=duration_sec,
            width=width,
            height=height,
            generation_time_sec=elapsed,
        )

    def _poll_for_completion(self, client: httpx.Client, video_id: str) -> str:
        """Poll HeyGen until video is complete, return the video URL."""
        elapsed = 0.0
        while elapsed < MAX_POLL_SEC:
            time.sleep(POLL_INTERVAL_SEC)
            elapsed += POLL_INTERVAL_SEC

            resp = client.get(
                f"{API_BASE}/v1/video_status.get",
                headers=self._headers,
                params={"video_id": video_id},
            )
            resp.raise_for_status()
            data = resp.json()["data"]
            status = data.get("status", "")

            if status == "completed":
                video_url = data["video_url"]
                log.info("heygen_completed", video_id=video_id, poll_sec=elapsed)
                return video_url
            elif status == "failed":
                error = data.get("error", "unknown")
                raise RuntimeError(f"HeyGen video {video_id} failed: {error}")
            else:
                if int(elapsed) % 30 == 0:
                    log.debug("heygen_polling", status=status, elapsed=elapsed)

        raise TimeoutError(
            f"HeyGen video {video_id} did not complete within {MAX_POLL_SEC}s"
        )


def _probe_video(path: Path) -> tuple[float, int, int]:
    """Get duration, width, height from a video file via moviepy (ffprobe fallback)."""
    try:
        from moviepy import VideoFileClip

        clip = VideoFileClip(str(path))
        duration = clip.duration
        width, height = clip.size
        clip.close()
        return duration, width, height
    except Exception:
        pass

    # Fallback to ffprobe if available
    try:
        probe = subprocess.run(
            [
                "ffprobe", "-v", "quiet",
                "-show_entries", "format=duration:stream=width,height",
                "-of", "json",
                str(path),
            ],
            capture_output=True,
            text=True,
        )
        if probe.stdout:
            info = json.loads(probe.stdout)
            duration = float(info.get("format", {}).get("duration", 0))
            streams = info.get("streams", [{}])
            width = streams[0].get("width", 0) if streams else 0
            height = streams[0].get("height", 0) if streams else 0
            return duration, width, height
    except FileNotFoundError:
        pass

    return 0.0, 0, 0
