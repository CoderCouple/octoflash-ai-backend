"""
Manim runner — bridges TemplateRenderer to an actual Manim render.

Architecture:
  ManimRunnerService.render() builds a TemplateRenderer for the requested
  (template, params, style, extra_steps), constructs an OctoflashScene that
  embeds it, configures Manim via tempconfig, and invokes scene.render().
  Manim writes an MP4 to disk; we probe it for duration/size/frames and
  return a RenderResult.

Primitives can't be async (Manim is sync) and shouldn't import Manim at
module-load time (that's heavy). Per-primitive lazy imports keep startup fast.
"""

from __future__ import annotations

import logging
import os
import subprocess
import uuid
from dataclasses import dataclass
from typing import Any

from app.settings import settings
from app.templates.renderer import TemplateRenderer

logger = logging.getLogger(__name__)


@dataclass
class RenderResult:
    video_path: str
    audio_path: str | None
    duration: float
    frame_count: int
    file_size: int
    snapshot: dict[str, Any]


def _probe_mp4(path: str) -> tuple[float, int]:
    """Use ffprobe to extract (duration_seconds, frame_count) from an MP4."""
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-select_streams",
        "v:0",
        "-show_entries",
        "stream=duration,nb_frames",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        path,
    ]
    out = subprocess.check_output(cmd).decode().strip().split("\n")
    duration = float(out[0])
    frame_count = int(out[1]) if len(out) > 1 and out[1] != "N/A" else 0
    return duration, frame_count


_QUALITY_MAP = {
    "low_quality": "low_quality",
    "medium_quality": "medium_quality",
    "high_quality": "high_quality",
    "production_quality": "production_quality",
}


class ManimRunnerService:
    def __init__(self) -> None:
        self.output_dir = settings.manim_output_dir
        self.preview_quality = settings.manim_quality_preview
        self.export_quality = settings.manim_quality_export

    def render(
        self,
        template_id: str,
        params: dict[str, Any],
        style: str | None = None,
        extra_steps: list[dict[str, Any]] | None = None,
        quality: str = "preview",
        seed: int | None = None,
    ) -> RenderResult:
        """Render one scene → MP4 on local disk. Sync; wrap in asyncio.to_thread()."""
        # Lazy import — Manim pulls in Cairo/Pango at import time.
        from manim import config as manim_config
        from manim import tempconfig

        from app.service.manim_scene import OctoflashScene

        # Bridge extra_steps (jsonb) → StepSpec list expected by the renderer.
        from app.templates.schema import StepSpec

        typed_extra_steps = [StepSpec.model_validate(s) for s in (extra_steps or [])]

        renderer = TemplateRenderer(
            template_id=template_id,
            params=params,
            style=style,
            extra_steps=typed_extra_steps,
        )

        # Unique output id so parallel renders never collide on disk.
        output_filename = f"render_{uuid.uuid4().hex}"
        quality_key = (
            self.preview_quality if quality == "preview" else self.export_quality
        )
        media_dir = os.path.abspath(self.output_dir)
        os.makedirs(media_dir, exist_ok=True)

        snapshot_holder: dict[str, Any] = {}

        with tempconfig(
            {
                "quality": _QUALITY_MAP.get(quality_key, "low_quality"),
                "output_file": output_filename,
                "media_dir": media_dir,
                "verbosity": "WARNING",
                "disable_caching": True,
                # Avoid Manim's interactive features in worker context.
                "preview": False,
                "write_to_movie": True,
            }
        ):
            scene = OctoflashScene(renderer=renderer, snapshot_sink=snapshot_holder)
            scene.render()

            # Manim writes to media_dir/videos/<output_file>/<quality>/output_filename.mp4
            # The exact subpath uses the resolution suffix per quality preset.
            video_path = self._locate_output(media_dir, output_filename)

        duration, frame_count = _probe_mp4(video_path)
        file_size = os.path.getsize(video_path)
        logger.info(
            "Manim render done: template=%s style=%s file=%s (%.2fs, %d frames, %d bytes)",
            template_id, style, video_path, duration, frame_count, file_size,
        )
        return RenderResult(
            video_path=video_path,
            audio_path=None,
            duration=duration,
            frame_count=frame_count,
            file_size=file_size,
            snapshot=snapshot_holder.get("snapshot", {}),
        )

    @staticmethod
    def _locate_output(media_dir: str, output_filename: str) -> str:
        """Find the MP4 Manim just wrote — its subpath depends on quality preset."""
        # Manim's layout: media_dir/videos/<temp_name>/<resolution>/<output_filename>.mp4
        # The <temp_name> comes from the Scene's class name; <resolution> from quality.
        # Easiest: walk videos/ and find the file by name.
        videos_root = os.path.join(media_dir, "videos")
        for root, _dirs, files in os.walk(videos_root):
            for f in files:
                if f == f"{output_filename}.mp4":
                    return os.path.join(root, f)
        raise FileNotFoundError(
            f"Manim render finished but no MP4 named {output_filename}.mp4 under {videos_root}"
        )
