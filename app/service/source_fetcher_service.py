"""
SourceFetcherService — pick a fetcher based on the URL.

Given a pasted URL, identify the source type (YouTube long-form, YouTube short,
Medium article, Substack article) and dispatch to the right per-source service.

Each fetcher returns a normalized `SourceContent`:
  - text:     the article body or video transcript
  - frames:   optional list of local image paths (video sources only; populated
              in later phases when keyframe extraction lands)
  - metadata: title, author, duration, etc.

Phase 1: this dispatcher exists with no real fetcher behind it. Each branch
raises `NotImplementedError` until later phases wire the per-source services.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from urllib.parse import urlparse


class SourceType(str, Enum):
    YOUTUBE_LONG = "youtube_long"   # standard /watch or /v/ video
    YOUTUBE_SHORT = "youtube_short"  # /shorts/<id>
    MEDIUM = "medium"
    SUBSTACK = "substack"


class UnsupportedSourceError(ValueError):
    """The pasted URL doesn't match any supported source pattern."""


@dataclass
class SourceContent:
    """Normalized output of any source fetcher."""

    source_type: SourceType
    source_url: str
    title: str
    text: str                             # main body / transcript
    author: str | None = None
    duration_seconds: int | None = None   # video sources only
    published_at: str | None = None       # ISO 8601 when known
    frames: list[str] = field(default_factory=list)  # local file paths
    extra: dict[str, str] = field(default_factory=dict)


# ─── URL classification ────────────────────────────────────────────────────────


def _host_matches(host: str, root: str) -> bool:
    """True if `host` is `root` or any subdomain of `root` (e.g. 'a.b.medium.com' for root 'medium.com')."""
    host = host.lower()
    root = root.lower()
    return host == root or host.endswith(f".{root}")


def classify_source_url(url: str) -> SourceType:
    """Return the SourceType for a pasted URL. Raises if unsupported."""
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    path = parsed.path or ""

    # YouTube — distinguish shorts from long-form via path segment.
    if _host_matches(host, "youtube.com") or host in ("youtu.be", "m.youtube.com"):
        if "/shorts/" in path:
            return SourceType.YOUTUBE_SHORT
        return SourceType.YOUTUBE_LONG

    if _host_matches(host, "medium.com"):
        return SourceType.MEDIUM

    # *.substack.com only — custom-domain Substack blogs would need an HTTP probe.
    if _host_matches(host, "substack.com"):
        return SourceType.SUBSTACK

    raise UnsupportedSourceError(
        f"Unsupported source URL: {url!r}. "
        "Supported: YouTube (long-form + shorts), Medium articles, Substack articles."
    )


# ─── Dispatcher ────────────────────────────────────────────────────────────────


class SourceFetcherService:
    """Picks the right per-source fetcher and returns a SourceContent."""

    async def fetch(self, source_url: str) -> SourceContent:
        source_type = classify_source_url(source_url)
        if source_type in (SourceType.YOUTUBE_LONG, SourceType.YOUTUBE_SHORT):
            return await self._fetch_youtube(source_url, source_type)
        if source_type == SourceType.MEDIUM:
            return await self._fetch_medium(source_url)
        if source_type == SourceType.SUBSTACK:
            return await self._fetch_substack(source_url)
        raise UnsupportedSourceError(f"Unhandled source type: {source_type}")

    async def _fetch_youtube(
        self, url: str, kind: SourceType
    ) -> SourceContent:
        import asyncio

        from app.service.transcript_service import TranscriptService

        # Metadata (title, duration, channel) + transcript in parallel.
        meta_task = asyncio.create_task(asyncio.to_thread(_fetch_youtube_metadata, url))
        transcript_task = asyncio.create_task(
            asyncio.to_thread(TranscriptService().fetch, url)
        )
        meta, transcript = await asyncio.gather(meta_task, transcript_task)

        return SourceContent(
            source_type=kind,
            source_url=url,
            title=meta.get("title") or "Untitled video",
            text=transcript.text,
            author=meta.get("channel"),
            duration_seconds=meta.get("duration"),
            published_at=meta.get("upload_date"),
            extra={"transcript_source": transcript.source},
        )

    async def _fetch_medium(self, url: str) -> SourceContent:
        import asyncio

        from app.service.article_scraper_service import ArticleScraperService

        article = await asyncio.to_thread(ArticleScraperService().fetch_medium, url)
        return SourceContent(
            source_type=SourceType.MEDIUM,
            source_url=url,
            title=article.title,
            text=article.text,
            author=article.author,
            published_at=article.published_at,
        )

    async def _fetch_substack(self, url: str) -> SourceContent:
        import asyncio

        from app.service.article_scraper_service import ArticleScraperService

        article = await asyncio.to_thread(ArticleScraperService().fetch_substack, url)
        return SourceContent(
            source_type=SourceType.SUBSTACK,
            source_url=url,
            title=article.title,
            text=article.text,
            author=article.author,
            published_at=article.published_at,
        )


# ─── YouTube metadata helper (sync — wrap in to_thread) ────────────────────────


def _fetch_youtube_metadata(url: str) -> dict:
    """Pull title, channel, duration, upload_date for a single video via yt-dlp."""
    import yt_dlp  # type: ignore

    opts = {
        "quiet": True,
        "skip_download": True,
        "no_warnings": True,
        "noplaylist": True,
        # Default extraction (not flat) so we get full metadata.
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=False)
    if not isinstance(info, dict):
        return {}
    # `upload_date` is YYYYMMDD; normalize to ISO 8601 if present.
    upload_date = info.get("upload_date")
    if upload_date and len(upload_date) == 8:
        upload_date = f"{upload_date[:4]}-{upload_date[4:6]}-{upload_date[6:8]}"
    return {
        "title": info.get("title"),
        "channel": info.get("uploader") or info.get("channel"),
        "duration": int(info["duration"]) if info.get("duration") else None,
        "upload_date": upload_date,
        "view_count": info.get("view_count"),
    }
