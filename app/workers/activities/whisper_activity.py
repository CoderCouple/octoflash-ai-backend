"""Whisper transcription for YouTube source URLs."""

from __future__ import annotations

from dataclasses import dataclass

from temporalio import activity


@dataclass
class TranscriptSegment:
    start: float
    end: float
    text: str


@dataclass
class TranscribeOutput:
    full_text: str
    segments: list[TranscriptSegment]
    language: str
    duration: float


@activity.defn(name="download_audio")
async def download_audio_activity(url: str) -> str:
    """yt-dlp → local audio path. Returns the path for the transcribe activity to consume."""
    raise NotImplementedError("yt-dlp activity not wired yet")


@activity.defn(name="transcribe_audio")
async def transcribe_audio_activity(audio_path: str) -> TranscribeOutput:
    """Run Whisper against a local audio file. Heavy; uses heartbeats."""
    raise NotImplementedError("Whisper activity not wired yet")
