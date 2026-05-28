"""YouTube channel + channel-videos fetcher.

Two-backend dispatcher invoked by SourceService.sync_videos:

  * **Data API v3** when `settings.youtube_api_key` is set — quota-based,
    structured JSON, stable. Preferred for production.

  * **yt-dlp fallback** when no key — works against any youtube.com URL
    (channel, @handle, user/, /c/, etc.), no quota, more brittle but free.
    Uses `--flat-playlist --dump-json --playlist-end N` to enumerate the
    channel's uploads cheaply (single HTTP request per ~30 videos).

The Source row stores `external_id` (UC… channel id) and `handle` from the
fetch. `source_url` is whatever URL the user pasted.

Surface:
  fetch_channel_metadata(source_url)
    → dict {external_id, handle, title, description, thumbnail_url,
            subscriber_count}
  fetch_channel_videos(external_id_or_url, max_videos)
    → list[dict] {external_id, source_url, title, description,
                  thumbnail_url, kind, duration_seconds, view_count,
                  published_at}

Sync only — callers should wrap in `asyncio.to_thread()` (yt-dlp + the
googleapiclient are blocking).
"""

from __future__ import annotations

import json
import logging
import subprocess
from datetime import datetime, timezone
from typing import Any

from app.settings import settings

log = logging.getLogger(__name__)


def _normalize_yt_thumbnail(url: str | None) -> str | None:
    """yt-dlp returns channel avatars with `=s0` (original-size) URLs that
    can be huge and inconsistent. Normalize the size token to s256-c so
    the FE gets a predictable 256×256 crop suitable for an avatar slot."""
    if not url:
        return url
    # googleusercontent URLs use `=sN` or `=sN-cN-...` parameters. Strip
    # everything after the first `=` and append a known-good size token.
    if "googleusercontent" in url and "=" in url:
        base = url.split("=", 1)[0]
        return f"{base}=s256-c"
    return url


class YouTubeFetcherService:
    """Channel metadata + channel-uploads listing via yt-dlp (or Data API v3
    when a key is configured)."""

    # Tunable: how aggressively yt-dlp pulls per video. flat-playlist gets
    # the cheap-but-incomplete listing (no view_count / published_at on
    # every backend). For prod we'd switch to the Data API v3.
    _YT_DLP_FLAGS = [
        "--quiet",
        "--no-warnings",
        "--ignore-errors",
        "--dump-json",
        "--flat-playlist",
    ]

    # ── channel metadata ──────────────────────────────────────────────

    def fetch_channel_metadata(self, source_url: str) -> dict[str, Any]:
        """Resolve a youtube.com URL to {external_id, handle, title, ...}.

        Uses yt-dlp's per-channel JSON dump (one request). Returns whatever
        fields YouTube exposes; the SourceService picks the ones it cares
        about. Raises RuntimeError on resolve failure.
        """
        result = subprocess.run(
            [
                "yt-dlp",
                "--quiet",
                "--no-warnings",
                "--skip-download",
                "--playlist-items", "0",   # don't pull videos, only channel info
                "--dump-single-json",
                source_url,
            ],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"yt-dlp failed to resolve channel {source_url!r}: "
                f"{result.stderr.strip()[-500:]}"
            )
        try:
            payload = json.loads(result.stdout)
        except json.JSONDecodeError as e:
            raise RuntimeError(
                f"yt-dlp produced invalid JSON for {source_url}: {e}"
            ) from e

        return {
            "external_id": payload.get("channel_id") or payload.get("uploader_id"),
            "handle":      payload.get("uploader_id") or payload.get("channel"),
            "title":       payload.get("channel") or payload.get("title") or "",
            "description": payload.get("description"),
            "thumbnail_url": _normalize_yt_thumbnail(
                (payload.get("thumbnails") or [{}])[-1].get("url"),
            ),
            "subscriber_count": payload.get("channel_follower_count"),
        }

    # ── channel videos ─────────────────────────────────────────────────

    def fetch_channel_videos(
        self,
        external_id_or_url: str,
        max_videos: int = 50,
    ) -> list[dict[str, Any]]:
        """Return up to `max_videos` recent uploads for a channel,
        spanning both the long-form `/videos` tab AND the `/shorts` tab.

        YouTube serves shorts from a separate tab — `/channel/UC…/videos`
        alone returns zero shorts even for channels that publish them
        constantly (Veritasium, MrBeast, etc). Fetch both and merge,
        deduping by video id.

        `external_id_or_url` accepts:
          * UC… channel id   → resolves to /channel/UC…/{videos,shorts}
          * a full channel URL (https://youtube.com/@handle, /c/, /user/, …)
        """
        if external_id_or_url.startswith("UC"):
            base = f"https://www.youtube.com/channel/{external_id_or_url}"
        else:
            base = external_id_or_url.rstrip("/")
            # If the caller already passed a tab-qualified URL, strip the
            # tab so we can append both tabs cleanly.
            for tab in ("/videos", "/shorts", "/streams", "/featured"):
                if base.endswith(tab):
                    base = base[: -len(tab)]
                    break

        tabs = [("/videos", "landscape"), ("/shorts", "short")]
        videos: list[dict[str, Any]] = []
        seen_ids: set[str] = set()
        # Split the budget across tabs so a high `max_videos` doesn't
        # blow past it after merging. Slight preference toward long-form.
        per_tab = max(5, max_videos // len(tabs))

        for tab_suffix, kind_hint in tabs:
            url = f"{base}{tab_suffix}"
            log.info(
                "YouTubeFetcherService.fetch_channel_videos: url=%s per_tab=%d",
                url, per_tab,
            )
            result = subprocess.run(
                [
                    "yt-dlp",
                    *self._YT_DLP_FLAGS,
                    "--playlist-end", str(per_tab),
                    url,
                ],
                capture_output=True,
                text=True,
                timeout=120,
            )
            if result.returncode != 0 and not result.stdout.strip():
                # Don't fatal here — a channel without shorts will fail
                # the /shorts tab and that's expected. Only fatal if
                # BOTH tabs come back empty (checked after the loop).
                log.warning(
                    "yt-dlp tab=%s returned nothing for %s: %s",
                    tab_suffix, base, result.stderr.strip()[-200:],
                )
                continue

            for line in result.stdout.splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    log.warning("yt-dlp emitted non-JSON line: %s", line[:120])
                    continue
                normalized = self._normalize_video_entry(entry, kind_hint=kind_hint)
                vid = normalized.get("external_id")
                if not vid or vid in seen_ids:
                    continue
                seen_ids.add(vid)
                videos.append(normalized)

        if not videos:
            raise RuntimeError(
                f"yt-dlp returned no videos for {base} across /videos + /shorts tabs"
            )

        log.info(
            "YouTubeFetcherService.fetch_channel_videos: parsed %d videos (%d shorts)",
            len(videos),
            sum(1 for v in videos if v.get("kind") == "short"),
        )
        return videos

    # ── helpers ────────────────────────────────────────────────────────

    @staticmethod
    def _normalize_video_entry(
        entry: dict[str, Any], *, kind_hint: str | None = None,
    ) -> dict[str, Any]:
        """Map a yt-dlp flat-playlist JSON line to our SourceVideo shape.

        `kind_hint` is the tab the entry came from ("short" / "landscape").
        We use it as a tiebreaker when yt-dlp's flat-playlist output omits
        `duration` (which is often does for shorts) — without it, every
        short would default to "landscape".
        """
        video_id = entry.get("id") or entry.get("video_id") or ""
        duration = entry.get("duration")
        try:
            duration_s = int(duration) if duration is not None else None
        except (TypeError, ValueError):
            duration_s = None

        # yt-dlp flat-playlist doesn't always include upload_date. When it
        # does, format is YYYYMMDD.
        published_at = None
        upload_date = entry.get("upload_date")
        if upload_date and len(str(upload_date)) == 8:
            try:
                published_at = datetime.strptime(str(upload_date), "%Y%m%d").replace(
                    tzinfo=timezone.utc,
                )
            except ValueError:
                pass

        # Pick the highest-quality thumbnail when the listing provides them.
        thumbs = entry.get("thumbnails") or []
        thumb_url: str | None = None
        if thumbs:
            thumb_url = thumbs[-1].get("url")
        else:
            thumb_url = entry.get("thumbnail")

        # Prefer the explicit duration cutoff when yt-dlp gave us one.
        # Fall back to the tab hint — entries from /shorts are
        # canonically shorts even when duration is missing.
        if duration_s is not None:
            kind = "short" if duration_s <= 75 else "landscape"
        else:
            kind = kind_hint or "landscape"

        return {
            "external_id":     video_id,
            "source_url":      entry.get("url") or f"https://www.youtube.com/watch?v={video_id}",
            "title":           entry.get("title") or "(untitled)",
            "description":     entry.get("description"),
            "thumbnail_url":   thumb_url,
            "kind":            kind,
            "duration_seconds": duration_s,
            "view_count":      entry.get("view_count"),
            "published_at":    published_at,
        }


# When/if a YouTube Data API v3 backend is added, dispatch here:
def get_youtube_fetcher() -> YouTubeFetcherService:
    """Factory. Returns the configured fetcher implementation.

    Today only the yt-dlp fallback is wired. When `settings.youtube_api_key`
    is set we'll add a `DataApiV3Fetcher(api_key=…)` branch and prefer it.
    """
    _ = settings.youtube_api_key  # touch so a future switch reads from settings
    return YouTubeFetcherService()
