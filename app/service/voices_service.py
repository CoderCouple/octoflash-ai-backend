"""Voices service — wraps the curated ElevenLabs catalog.

The catalog itself lives in `app/manim_pipeline/voices.py` so the Manim render
subprocess (which imports it under PYTHONPATH=app/manim_pipeline) can resolve
the same `voice_id → voice metadata` mapping as the API layer.
"""

from __future__ import annotations

from app.manim_pipeline.voices import DEFAULT_VOICE_ID, VOICE_CATALOG, find_voice, list_accents


class VoicesService:
    def list_voices(
        self,
        gender: str | None = None,
        accent: str | None = None,
    ) -> list[dict]:
        """Return catalog entries, optionally filtered by gender / accent."""
        voices = VOICE_CATALOG
        if gender:
            voices = [v for v in voices if v["gender"].lower() == gender.lower()]
        if accent:
            voices = [v for v in voices if v["accent"].lower() == accent.lower()]
        return list(voices)

    def get_voice(self, voice_id: str) -> dict | None:
        return find_voice(voice_id)

    def list_accents(self) -> list[str]:
        return list_accents()

    def default_voice_id(self) -> str:
        return DEFAULT_VOICE_ID
