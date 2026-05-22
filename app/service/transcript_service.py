"""
TranscriptService — get text from a YouTube video URL.

Strategy: try `youtube-transcript-api` first (free, ~1s, works for any video
with auto-captions or human captions). If that fails, fall back to **faster-whisper**:
download audio via yt-dlp → transcribe with `settings.whisper_model`.

Both paths are synchronous + network/CPU-bound. Callers should wrap in
`asyncio.to_thread(...)` from async code.

Phase 3 contract: returns a single `TranscriptResult` with concatenated text.
Per-segment timestamps are captured but not surfaced — they'll matter when
we wire scene-aligned summarization later.
"""

from __future__ import annotations

import logging
import os
import re
import tempfile
from dataclasses import dataclass, field
from urllib.parse import parse_qs, urlparse

from app.settings import settings

logger = logging.getLogger(__name__)


@dataclass
class TranscriptResult:
    text: str
    language: str | None = None
    source: str = ""  # "captions" | "whisper"
    duration_seconds: float | None = None
    segments: list[dict] = field(default_factory=list)


class TranscriptError(RuntimeError):
    """Both captions + Whisper failed (or the URL is unrecognized)."""


# ─── URL → video id ────────────────────────────────────────────────────────────


def extract_video_id(url: str) -> str:
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    path = parsed.path or ""

    if host == "youtu.be":
        return path.lstrip("/").split("/")[0]

    if host == "youtube.com" or host.endswith(".youtube.com"):
        for prefix in ("/shorts/", "/embed/", "/v/", "/live/"):
            if path.startswith(prefix):
                return path[len(prefix):].split("/")[0]
        # Standard /watch?v=...
        q = parse_qs(parsed.query)
        if "v" in q and q["v"]:
            return q["v"][0]

    raise ValueError(f"Could not extract YouTube video id from {url!r}")


# ─── Captions path (free, fast) ────────────────────────────────────────────────


def _parse_vtt(vtt_text: str) -> str:
    """Strip WEBVTT headers + timestamps; return concatenated caption text."""
    lines: list[str] = []
    for raw in vtt_text.splitlines():
        line = raw.strip()
        # Skip empty lines, headers, timestamp ranges, and cue ids.
        if not line:
            continue
        if line.startswith(("WEBVTT", "NOTE", "STYLE", "REGION", "Kind:", "Language:")):
            continue
        if "-->" in line:
            continue
        if line.isdigit():
            continue
        # Strip inline timestamp tags like <00:00:12.345> and <c> tags.
        line = re.sub(r"<[^>]+>", "", line)
        if line:
            lines.append(line)
    # Dedupe consecutive duplicate lines (common with auto-captions that repeat
    # rolling text across cues).
    deduped: list[str] = []
    for line in lines:
        if not deduped or deduped[-1] != line:
            deduped.append(line)
    text = " ".join(deduped)
    return re.sub(r"\s+", " ", text).strip()


def _via_captions(video_url: str, languages: list[str] | None = None) -> TranscriptResult:
    """Pull captions via yt-dlp's subtitle download.

    More reliable than youtube-transcript-api, which routinely gets throttled
    to empty XML responses from datacenter / repeated-request IPs. yt-dlp
    downloads the actual VTT subtitle file YouTube serves to the web player.
    """
    import yt_dlp  # type: ignore

    langs = languages or ["en", "en-US", "en-GB"]
    with tempfile.TemporaryDirectory(prefix="octoflash-captions-") as tmpdir:
        outtmpl = os.path.join(tmpdir, "video.%(ext)s")
        opts = {
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
            "writesubtitles": True,
            "writeautomaticsub": True,
            "subtitleslangs": langs,
            "subtitlesformat": "vtt",
            "outtmpl": outtmpl,
        }
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                ydl.extract_info(video_url, download=True)
        except Exception as e:
            raise TranscriptError(f"yt-dlp subtitle fetch failed: {e}") from e

        # Pick the first .vtt file produced.
        vtt_path = None
        chosen_lang = None
        for entry in sorted(os.listdir(tmpdir)):
            if entry.endswith(".vtt"):
                vtt_path = os.path.join(tmpdir, entry)
                # Filename: video.en.vtt → language "en".
                parts = entry.rsplit(".", 2)
                chosen_lang = parts[-2] if len(parts) >= 2 else None
                break
        if not vtt_path:
            raise TranscriptError("No captions available (auto or manual)")

        with open(vtt_path, encoding="utf-8") as f:
            vtt_text = f.read()

    text = _parse_vtt(vtt_text)
    if not text:
        raise TranscriptError("Captions parsed empty")

    return TranscriptResult(text=text, language=chosen_lang, source="captions")


# ─── Whisper fallback ──────────────────────────────────────────────────────────


def _download_audio(video_url: str, target_dir: str) -> str:
    """yt-dlp → bestaudio → m4a in target_dir. Returns the local path."""
    import yt_dlp  # type: ignore

    outtmpl = os.path.join(target_dir, "audio.%(ext)s")
    opts = {
        "quiet": True,
        "format": "bestaudio/best",
        "outtmpl": outtmpl,
        # Don't run any post-processors — faster-whisper reads the m4a directly.
        "noplaylist": True,
        "no_warnings": True,
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(video_url, download=True)
    # Resolve the actual filename yt-dlp chose.
    filename = ydl.prepare_filename(info) if info else None
    if not filename or not os.path.exists(filename):
        # Fallback: pick the first audio.* in the dir.
        for entry in os.listdir(target_dir):
            if entry.startswith("audio."):
                return os.path.join(target_dir, entry)
        raise TranscriptError("yt-dlp finished but no audio file was produced")
    return filename


def _via_whisper(video_url: str) -> TranscriptResult:
    from faster_whisper import WhisperModel  # type: ignore

    with tempfile.TemporaryDirectory(prefix="octoflash-whisper-") as tmpdir:
        audio_path = _download_audio(video_url, tmpdir)

        # Load once per call — model can be 1-3 GB; cache via lru would help but
        # workers should hold the model. For Phase 3 we accept the load cost on
        # each Whisper fallback (it's the slow path).
        model_name = settings.whisper_model
        compute_type = "int8"  # CPU-friendly; switch to "float16" on GPU
        logger.info("Loading Whisper model %s (compute_type=%s)", model_name, compute_type)
        model = WhisperModel(model_name, device="cpu", compute_type=compute_type)
        segments_iter, info = model.transcribe(audio_path, beam_size=5)
        segments = list(segments_iter)
        text = " ".join(s.text.strip() for s in segments).strip()
        if not text:
            raise TranscriptError("Whisper produced empty transcript")

        return TranscriptResult(
            text=text,
            language=info.language,
            source="whisper",
            duration_seconds=info.duration,
            segments=[
                {"text": s.text, "start": s.start, "duration": s.end - s.start}
                for s in segments
            ],
        )


# ─── Public orchestrator ───────────────────────────────────────────────────────


class TranscriptService:
    def fetch(self, video_url: str) -> TranscriptResult:
        """Try captions (yt-dlp); on failure, fall back to Whisper. Returns text + provenance."""
        try:
            return _via_captions(video_url)
        except TranscriptError as e:
            logger.info(
                "Captions unavailable for %s (%s); falling back to Whisper",
                video_url, e,
            )

        # If we got here, captions failed. Whisper is heavy — log loudly so
        # the operator knows where time is going.
        logger.warning("Whisper fallback engaging for %s — this can take minutes", video_url)
        return _via_whisper(video_url)
