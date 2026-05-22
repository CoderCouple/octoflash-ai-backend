"""
Frame extraction via ffmpeg.

Synchronous + subprocess-based. Callers in async code should wrap in
`asyncio.to_thread(...)`. Used by the analyze workflow to produce ~1 frame
per second from a downloaded source video; those frames are then fed to
Claude vision for the structured description.
"""

from __future__ import annotations

import json
import logging
import subprocess
from dataclasses import dataclass
from pathlib import Path

from app.settings import settings

logger = logging.getLogger(__name__)


@dataclass
class ExtractedFrames:
    frames_dir: Path
    frame_paths: list[Path]
    duration_seconds: float | None


class FrameExtractionError(RuntimeError):
    """ffmpeg / ffprobe failed or produced no frames."""


def get_video_duration(video_path: Path) -> float:
    """Read duration in seconds via ffprobe. Raises if ffprobe fails."""
    cmd = [
        "ffprobe",
        "-v", "quiet",
        "-print_format", "json",
        "-show_format",
        str(video_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if result.returncode != 0:
        raise FrameExtractionError(f"ffprobe failed: {result.stderr.strip()}")
    info = json.loads(result.stdout)
    return float(info["format"]["duration"])


def extract_frames(
    project_id: str,
    video_path: Path,
    fps: float = 1.0,
    quality: int = 2,
) -> ExtractedFrames:
    """Extract `fps` frames per second from `video_path` for `project_id`.

    Output: `<storage_root>/projects/{project_id}/frames/frame_NNNN.jpg`.
    Returns the frames directory + sorted list of frame paths + duration.
    """
    frames_dir = _get_frames_dir(project_id)
    frames_dir.mkdir(parents=True, exist_ok=True)

    # Clear any stale frames from a previous run.
    for stale in frames_dir.glob("frame_*.jpg"):
        stale.unlink()

    cmd = [
        "ffmpeg",
        "-i", str(video_path),
        "-vf", f"fps={fps}",
        "-q:v", str(quality),
        str(frames_dir / "frame_%04d.jpg"),
        "-y",
    ]
    logger.info("extract_frames: %s fps=%s -> %s", video_path, fps, frames_dir)
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    if result.returncode != 0:
        raise FrameExtractionError(f"ffmpeg failed: {result.stderr.strip()[-500:]}")

    frame_paths = sorted(frames_dir.glob("frame_*.jpg"))
    if not frame_paths:
        raise FrameExtractionError("ffmpeg produced no frames")

    # Duration is useful for the prompt builder and for clip-planning later.
    try:
        duration = get_video_duration(video_path)
    except FrameExtractionError as e:
        logger.warning("get_video_duration failed (%s) — falling back to frame count", e)
        duration = len(frame_paths) / fps if fps > 0 else None

    return ExtractedFrames(
        frames_dir=frames_dir,
        frame_paths=frame_paths,
        duration_seconds=duration,
    )


def _get_frames_dir(project_id: str) -> Path:
    """Resolve `<storage_root>/projects/{project_id}/frames/`."""
    storage_root = Path(settings.local_storage_path or "storage").resolve()
    return storage_root / "projects" / project_id / "frames"
