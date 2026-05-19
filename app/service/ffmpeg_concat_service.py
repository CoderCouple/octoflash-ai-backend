"""
FFmpeg concat — stitches per-scene MP4 clips into one output file.

Two modes:
  reencode=False (preview)  →  `-c copy` via the concat demuxer. Fast (seconds),
                                no quality loss, but requires every input to
                                share codec / resolution / framerate. Manim
                                outputs at a fixed quality preset are uniform,
                                so this works for our preview path.

  reencode=True  (export)   →  re-encode through libx264 (slow preset, CRF 18).
                                Slower (minutes for long videos) but normalizes
                                any mismatched inputs and produces a clean,
                                single-pass deliverable.

Audio: today no primitive emits audio, so we don't mux an audio track.
"""

from __future__ import annotations

import logging
import os
import shlex
import subprocess
import tempfile
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ConcatResult:
    output_path: str
    duration: float
    file_size: int


def _probe_duration(path: str) -> float:
    out = subprocess.check_output(
        [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            path,
        ]
    ).decode().strip()
    return float(out) if out else 0.0


class FFmpegConcatService:
    def concat(
        self,
        clip_paths: list[str],
        output_path: str,
        reencode: bool = False,
    ) -> ConcatResult:
        if not clip_paths:
            raise ValueError("concat requires at least one clip")
        for p in clip_paths:
            if not os.path.isfile(p):
                raise FileNotFoundError(f"clip not found: {p}")

        os.makedirs(os.path.dirname(os.path.abspath(output_path)) or ".", exist_ok=True)

        with tempfile.TemporaryDirectory(prefix="octoflash-concat-") as tmpdir:
            list_path = os.path.join(tmpdir, "list.txt")
            with open(list_path, "w") as f:
                for clip in clip_paths:
                    # ffmpeg concat demuxer requires `file 'abs/path'` per line; single-quote-escape.
                    abs_clip = os.path.abspath(clip).replace("'", r"'\''")
                    f.write(f"file '{abs_clip}'\n")

            if reencode:
                cmd = [
                    "ffmpeg", "-y",
                    "-f", "concat", "-safe", "0", "-i", list_path,
                    "-c:v", "libx264", "-preset", "slow", "-crf", "18",
                    "-pix_fmt", "yuv420p",
                    "-movflags", "+faststart",
                    "-an",  # explicit no audio
                    output_path,
                ]
            else:
                cmd = [
                    "ffmpeg", "-y",
                    "-f", "concat", "-safe", "0", "-i", list_path,
                    "-c", "copy",
                    "-an",
                    output_path,
                ]

            logger.info("ffmpeg concat: %s", " ".join(shlex.quote(a) for a in cmd))
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                raise RuntimeError(
                    f"ffmpeg concat failed (exit {result.returncode}):\n"
                    f"{result.stderr[-2000:]}"
                )

        duration = _probe_duration(output_path)
        file_size = os.path.getsize(output_path)
        logger.info(
            "concat done: %s (%.2fs, %d bytes, reencode=%s, %d clips)",
            output_path, duration, file_size, reencode, len(clip_paths),
        )
        return ConcatResult(
            output_path=output_path, duration=duration, file_size=file_size
        )
