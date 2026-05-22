"""
Describer — Claude vision on source frames + transcript → structured description.

Thin wrapper over `script_generator_service.analyze_source_frames`. Lives in its
own module so the analyze workflow can depend on it without pulling the whole
script-generation surface.
"""

from __future__ import annotations

import logging

from app.service.script_generator_service import analyze_source_frames

logger = logging.getLogger(__name__)


class DescriberService:
    async def describe(
        self,
        frame_paths: list[str],
        transcript: str,
        duration: float,
    ) -> str:
        """Send sampled frames + transcript to Claude vision, return the structured description.

        `frame_paths` are paths relative to settings.local_storage_path (matches
        the MVP convention so the underlying analyze_source_frames can resolve them).
        """
        return await analyze_source_frames(frame_paths, transcript, duration)
