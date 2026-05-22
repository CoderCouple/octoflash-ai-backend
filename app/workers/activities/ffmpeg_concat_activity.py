"""
FFmpeg concat activity — stitch per-clip MP4s into one final video.

Pure subprocess work; wrapped in asyncio.to_thread so it doesn't block the
event loop. Returns the output path; the workflow writes it onto
Project.final_video_url via update_project_activity.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path

from temporalio import activity

from app.service.ffmpeg_concat_service import concat_clips
from app.settings import settings


@dataclass
class FFmpegConcatInput:
    project_id: str
    clip_paths: list[str]  # ordered list of per-clip MP4 paths
    orientation: str = "portrait"  # used to pick output dir


@dataclass
class FFmpegConcatOutput:
    output_path: str
    clip_count: int
    size_bytes: int


@activity.defn(name="ffmpeg_concat")
async def ffmpeg_concat_activity(payload: FFmpegConcatInput) -> FFmpegConcatOutput:
    """Concatenate ordered per-clip MP4s into storage/projects/<id>/final.mp4."""
    activity.logger.info(
        "ffmpeg_concat: project=%s clips=%d orient=%s",
        payload.project_id, len(payload.clip_paths), payload.orientation,
    )

    storage_root = Path(settings.local_storage_path or "storage").resolve()
    output_path = (
        storage_root / "projects" / payload.project_id / f"final_{payload.orientation}.mp4"
    )

    paths = [Path(p) for p in payload.clip_paths]
    out = await asyncio.to_thread(concat_clips, paths, output_path)

    size = out.stat().st_size
    activity.logger.info("ffmpeg_concat done: %s (%d bytes)", out, size)
    return FFmpegConcatOutput(
        output_path=str(out),
        clip_count=len(paths),
        size_bytes=size,
    )
