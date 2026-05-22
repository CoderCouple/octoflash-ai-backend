"""YouTube channel-metadata + channel-videos fetcher via yt-dlp.

Surface used by ChannelService (sync — callers wrap in `asyncio.to_thread`):
  - fetch_channel_metadata(source_url) → dict {title, external_id, ...}
  - fetch_channel_videos(external_id, max_videos) → list[dict]

This is a thin stub re-introduced after the abstraction cleanup. The real
implementation will land alongside the analyze workflow port (task 12) using
the MVP's yt-dlp channel-shorts listing logic.
"""

from __future__ import annotations


class YouTubeFetcherService:
    def fetch_channel_metadata(self, source_url: str) -> dict:
        raise NotImplementedError(
            "YouTube channel metadata fetch not wired yet — pending task 12."
        )

    def fetch_channel_videos(self, external_id: str, max_videos: int) -> list[dict]:
        raise NotImplementedError(
            "YouTube channel video listing not wired yet — pending task 12."
        )
