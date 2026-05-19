"""
Whisper runner — transcribes audio from a YouTube URL (or local audio file)
when the project source is a URL rather than a freeform prompt.

Output feeds PlannerService.plan_from_transcript().
"""

from dataclasses import dataclass

from app.settings import settings


@dataclass
class TranscriptSegment:
    start: float
    end: float
    text: str


@dataclass
class TranscriptResult:
    full_text: str
    segments: list[TranscriptSegment]
    language: str
    duration: float


class WhisperRunnerService:
    def __init__(self) -> None:
        self.model_name = settings.whisper_model

    def transcribe(self, audio_path: str) -> TranscriptResult:
        """Transcribe a local audio file."""
        # TODO: whisper.load_model(self.model_name).transcribe(audio_path)
        raise NotImplementedError("Whisper transcription not wired yet")

    def transcribe_url(self, url: str) -> TranscriptResult:
        """Download audio from a YouTube URL (via yt-dlp) then transcribe."""
        # TODO: yt-dlp to extract audio, then call self.transcribe()
        raise NotImplementedError("URL transcription not wired yet")
