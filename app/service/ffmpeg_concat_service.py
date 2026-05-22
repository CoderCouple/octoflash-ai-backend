"""
FFmpeg concat — stitch per-clip MP4s into the final video.

Uses ffmpeg's concat demuxer with `-c copy` so it's a stream-level join (no
re-encode). Takes seconds even for long videos. Only works if every input clip
has identical resolution, framerate, and codec — which they will when they all
came out of the same Manim render pipeline with the same orientation + quality.
"""

from __future__ import annotations

import logging
import subprocess
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)


class FFmpegConcatError(RuntimeError):
    """ffmpeg returned non-zero or produced no output."""


def concat_clips(
    clip_paths: list[Path],
    output_path: Path,
    timeout_seconds: int = 120,
) -> Path:
    """Concatenate `clip_paths` (in order) into `output_path`. Sync.

    Returns the output path on success. Raises FFmpegConcatError on failure.
    All clips must share resolution / framerate / codec — i.e. they all came
    out of the same Manim quality preset and orientation. The function does
    not verify this; ffmpeg will fail loudly if mismatched.
    """
    if not clip_paths:
        raise FFmpegConcatError("concat_clips called with empty clip list")

    # Filter to existing files; warn about any missing
    existing = [p for p in clip_paths if p.exists()]
    missing = [p for p in clip_paths if not p.exists()]
    if missing:
        logger.warning(
            "concat_clips: %d/%d input clips missing from disk; skipping:\n%s",
            len(missing), len(clip_paths),
            "\n".join(f"  - {p}" for p in missing),
        )
    if not existing:
        raise FFmpegConcatError(f"no input clips exist on disk (asked for {len(clip_paths)})")

    output_path.parent.mkdir(parents=True, exist_ok=True)

    # ffmpeg concat demuxer wants a text file with `file '<path>'` per line.
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".txt", delete=False, prefix="octoflash-concat-"
    ) as fh:
        list_file = Path(fh.name)
        for p in existing:
            # Use absolute paths so the demuxer works regardless of cwd.
            fh.write(f"file '{p.resolve()}'\n")
    logger.info("concat list file: %s (%d clips)", list_file, len(existing))

    cmd = [
        "ffmpeg",
        "-y",  # overwrite output
        "-f", "concat",
        "-safe", "0",  # allow absolute paths in the list file
        "-i", str(list_file),
        "-c", "copy",
        str(output_path),
    ]
    logger.info("ffmpeg concat cmd: %s", " ".join(cmd))

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
    finally:
        list_file.unlink(missing_ok=True)

    if result.returncode != 0:
        logger.error(
            "ffmpeg concat failed: returncode=%d\n--- stderr (last 2000) ---\n%s",
            result.returncode, result.stderr[-2000:],
        )
        raise FFmpegConcatError(
            f"ffmpeg concat exited {result.returncode}: {result.stderr.strip()[-500:]}"
        )

    if not output_path.exists():
        raise FFmpegConcatError(f"ffmpeg returned 0 but {output_path} doesn't exist")

    size_mb = output_path.stat().st_size / (1024 * 1024)
    logger.info(
        "ffmpeg concat done: %s (%.2f MB from %d clips)",
        output_path, size_mb, len(existing),
    )
    return output_path
