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
from app.service.supabase_storage_service import BUCKET_RENDERS, get_storage_service
from app.settings import settings


@dataclass
class FFmpegConcatInput:
    project_id: str
    clip_paths: list[str]  # ordered list of per-clip MP4 paths
    orientation: str = "portrait"  # used to pick output dir


@dataclass
class FFmpegConcatOutput:
    """Returned by the activity.

    `output_path` is the virtual reference written onto
    `Project.final_<orientation>_video_url`. With Supabase Storage wired
    it always has the form `supabase://renders/<bucket-relative-path>`.
    The preview endpoint re-signs this on every request — signed URLs
    are time-limited so we never persist them.
    """

    output_path: str
    clip_count: int
    size_bytes: int


@activity.defn(name="ffmpeg_concat")
async def ffmpeg_concat_activity(payload: FFmpegConcatInput) -> FFmpegConcatOutput:
    """Concatenate ordered per-clip MP4s, upload the result to Supabase
    Storage, and return the bucket-relative reference."""
    activity.logger.info(
        "ffmpeg_concat: project=%s clips=%d orient=%s",
        payload.project_id, len(payload.clip_paths), payload.orientation,
    )

    storage_root = Path(settings.local_storage_path or "storage").resolve()
    local_output = (
        storage_root / "projects" / payload.project_id / f"final_{payload.orientation}.mp4"
    )

    paths = [Path(p) for p in payload.clip_paths]
    stitched = await asyncio.to_thread(concat_clips, paths, local_output)
    size = stitched.stat().st_size

    # Upload to Supabase Storage `renders` bucket. Path mirrors the
    # local layout so worker logs + Supabase dashboard line up.
    bucket_path = f"projects/{payload.project_id}/final_{payload.orientation}.mp4"
    storage = get_storage_service()
    await asyncio.to_thread(
        storage.upload_file,
        bucket=BUCKET_RENDERS,
        path=bucket_path,
        local_path=str(stitched),
        content_type="video/mp4",
    )
    activity.logger.info(
        "ffmpeg_concat uploaded: bucket=%s path=%s bytes=%d",
        BUCKET_RENDERS, bucket_path, size,
    )

    return FFmpegConcatOutput(
        output_path=f"supabase://{BUCKET_RENDERS}/{bucket_path}",
        clip_count=len(paths),
        size_bytes=size,
    )
