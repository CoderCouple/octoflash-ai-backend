"""FFmpeg concat — stitches selected variations into a preview/export MP4."""

from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass

from temporalio import activity


@dataclass
class ConcatClipsInput:
    clip_paths: list[str]  # local paths, ordered (must match scene order)
    # The activity resolves the absolute output path under the worker's media dir.
    # Workflows can't compute filesystem paths (sandbox restriction), so they
    # pass just a relative name like "previews/project_x_job_y.mp4".
    output_relative_name: str
    reencode: bool = False  # True for export (normalize codec), False for preview


@dataclass
class ConcatClipsOutput:
    output_path: str
    duration: float
    file_size: int


@activity.defn(name="concat_clips")
async def concat_clips_activity(payload: ConcatClipsInput) -> ConcatClipsOutput:
    """Run FFmpeg concat. Long-running for big exports — runs in a thread to
    keep the worker responsive to heartbeats."""
    activity.heartbeat({"phase": "concat_start", "clip_count": len(payload.clip_paths)})

    from app.service.ffmpeg_concat_service import FFmpegConcatService
    from app.settings import settings

    media_dir = os.path.abspath(settings.manim_output_dir)
    output_path = os.path.join(media_dir, "concat", payload.output_relative_name)

    service = FFmpegConcatService()
    result = await asyncio.to_thread(
        service.concat,
        payload.clip_paths,
        output_path,
        payload.reencode,
    )

    activity.heartbeat({"phase": "concat_done"})
    return ConcatClipsOutput(
        output_path=result.output_path,
        duration=result.duration,
        file_size=result.file_size,
    )
