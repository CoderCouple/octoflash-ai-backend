"""
FFmpeg concat — stitch per-clip MP4s into the final video.

Uses ffmpeg's concat demuxer with `-c copy` for a fast stream-level join (no
video re-encode). All clips must share resolution / framerate / video codec
— which they do because they all came out of the same Manim render pipeline
with the same orientation + quality preset.

Audio is the gotcha. The clip planner runs voiceover=True but the
script-generator's retry chain can fall back to a no-voice scene class
after exhausting attempts (`claude_novoice_fresh`). When you concat a mix
of audio-bearing and silent clips with `-c copy`, ffmpeg's demuxer requires
every input to have the **same** stream layout — so it silently drops the
audio track entirely, producing a video-only final even when most clips
have voice. We've seen this on real runs (prj_42a2224b: 5 voiced + 3
no-voice clips → 0 audio streams in the final).

Fix: before concat, normalize each clip to have exactly 1 video + 1 audio
stream. Audio-bearing clips pass through; silent clips get a synthesized
silent AAC track grafted on (no video re-encode, ~1s per clip). Then the
concat-demuxer happily produces a final with audio everywhere.
"""

from __future__ import annotations

import logging
import subprocess
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)


# Silent-audio target — what we splice onto clips that have no audio so
# the concat list is layout-homogeneous. AAC stereo 44.1 kHz matches
# manim-voiceover's default output codec, so the demuxer can copy
# without re-encode.
_SILENT_AUDIO_CODEC = "aac"
_SILENT_AUDIO_BITRATE = "128k"
_SILENT_AUDIO_LAVFI = "anullsrc=channel_layout=stereo:sample_rate=44100"


class FFmpegConcatError(RuntimeError):
    """ffmpeg returned non-zero or produced no output."""


def _has_audio_stream(path: Path) -> bool:
    """Return True if `path` has at least one audio stream. Quick ffprobe."""
    try:
        result = subprocess.run(
            [
                "ffprobe", "-v", "error",
                "-select_streams", "a:0",
                "-show_entries", "stream=codec_type",
                "-of", "csv=p=0",
                str(path),
            ],
            capture_output=True, text=True, timeout=10,
        )
    except subprocess.TimeoutExpired:
        return False
    return result.returncode == 0 and "audio" in (result.stdout or "")


def _normalize_for_concat(input_path: Path) -> Path:
    """Ensure `input_path` has a video + audio stream. If it already does,
    return it unchanged. Otherwise produce a sibling `.normalized.mp4` that
    pairs the original video with a synthesized silent AAC track of matching
    duration. The `-shortest` flag clips the silence to the video's length.

    Video is `-c:v copy` so no re-encode. Audio is AAC at 128 kbit — matches
    manim-voiceover's output format so a downstream `-c copy` concat works.
    """
    if _has_audio_stream(input_path):
        return input_path

    out = input_path.with_name(f"{input_path.stem}.with_silence.mp4")
    cmd = [
        "ffmpeg", "-y",
        "-i", str(input_path),
        "-f", "lavfi", "-i", _SILENT_AUDIO_LAVFI,
        "-map", "0:v",
        "-map", "1:a",
        "-c:v", "copy",
        "-c:a", _SILENT_AUDIO_CODEC,
        "-b:a", _SILENT_AUDIO_BITRATE,
        "-shortest",
        str(out),
    ]
    logger.info("concat: normalizing %s → silent-audio (%s)", input_path.name, out.name)
    result = subprocess.run(
        cmd, capture_output=True, text=True, timeout=60, check=False,
    )
    if result.returncode != 0 or not out.exists():
        logger.error(
            "concat: silent-audio normalize failed for %s rc=%d:\n%s",
            input_path, result.returncode, result.stderr[-1500:],
        )
        # Fall back to the original. Concat will likely drop audio for the
        # whole final, but better that than failing the whole render.
        return input_path
    return out


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

    # Pre-normalize: any clip missing an audio stream gets a silent AAC
    # track grafted on so the concat demuxer sees a homogeneous layout.
    # Without this, mixed audio/no-audio inputs cause ffmpeg to silently
    # drop the audio track from the final.
    normalized = [_normalize_for_concat(p) for p in existing]
    voiced = sum(1 for p in existing if _has_audio_stream(p))
    if voiced != len(existing):
        logger.info(
            "concat: %d/%d clips had audio; %d silenced clips were grafted",
            voiced, len(existing), len(existing) - voiced,
        )

    # ffmpeg concat demuxer wants a text file with `file '<path>'` per line.
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".txt", delete=False, prefix="octoflash-concat-"
    ) as fh:
        list_file = Path(fh.name)
        for p in normalized:
            # Use absolute paths so the demuxer works regardless of cwd.
            fh.write(f"file '{p.resolve()}'\n")
    logger.info("concat list file: %s (%d clips)", list_file, len(normalized))

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
