"""
YouTubeFetcherService — extract channel metadata + recent videos from a URL.

Strategy: prefer the official **YouTube Data API v3** when `youtube_api_key`
is set (reliable, structured, but quota-limited). Fall back to **yt-dlp**
(no key, no quota, brittle if YouTube changes their page layout).

Public surface:
    fetch_channel_metadata(source_url) -> ChannelMeta
    fetch_channel_videos(external_id, max_results) -> list[VideoMeta]

Both are synchronous + network-bound. Callers should wrap in
`asyncio.to_thread(...)` from async code.

Detection of "shorts" vs "landscape":
    - Source URL contains `/shorts/<id>` → short
    - Else "landscape" (yt-dlp `was_live`, livestreams, etc. all default to
      landscape; can be refined later by inspecting aspect ratio)
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from app.settings import settings

logger = logging.getLogger(__name__)


@dataclass
class ChannelMeta:
    name: str
    external_id: str | None  # YouTube channel id (UC...)
    handle: str | None       # @username if available
    description: str | None = None
    thumbnail_url: str | None = None
    subscriber_count: int | None = None
    source_url: str = ""


@dataclass
class VideoMeta:
    external_id: str
    source_url: str
    title: str
    kind: str = "landscape"  # "short" | "landscape"
    description: str | None = None
    thumbnail_url: str | None = None
    duration_seconds: int | None = None
    view_count: int | None = None
    published_at: datetime | None = None
    extra: dict[str, Any] = field(default_factory=dict)


# ─── URL helpers ───────────────────────────────────────────────────────────────


_CHANNEL_URL_PATTERNS = [
    # /channel/UCxxxx
    re.compile(r"youtube\.com/channel/(?P<id>UC[\w-]{20,})"),
    # /@handle
    re.compile(r"youtube\.com/(?P<handle>@[\w.\-]+)"),
    # /c/customname  /  /user/legacyname (rare; fetcher resolves via API/yt-dlp)
    re.compile(r"youtube\.com/(?:c|user)/(?P<custom>[\w.\-]+)"),
]


def parse_channel_url(url: str) -> dict[str, str | None]:
    """Best-effort: extract any of {channel_id, handle, custom} from a YT URL."""
    for pat in _CHANNEL_URL_PATTERNS:
        m = pat.search(url)
        if m:
            return {k: m.groupdict().get(k) for k in ("id", "handle", "custom")}
    return {"id": None, "handle": None, "custom": None}


def _is_shorts_url(url: str) -> bool:
    return "/shorts/" in url


# ─── Fetcher ───────────────────────────────────────────────────────────────────


class YouTubeFetcherService:
    def __init__(self) -> None:
        self.api_key = settings.youtube_api_key
        self.max_videos = settings.channel_sync_max_videos

    # ── Public API ─────────────────────────────────────────────────────────

    def fetch_channel_metadata(self, source_url: str) -> ChannelMeta:
        """Resolve a pasted channel URL → ChannelMeta."""
        if self.api_key:
            try:
                return self._meta_via_api(source_url)
            except Exception as e:
                logger.warning(
                    "YouTube API metadata fetch failed (%s); falling back to yt-dlp",
                    type(e).__name__,
                )
        return self._meta_via_ytdlp(source_url)

    def fetch_channel_videos(
        self, external_id: str, max_results: int | None = None
    ) -> list[VideoMeta]:
        """Recent videos for a channel id. Returns up to `max_results` items."""
        limit = max_results or self.max_videos
        if self.api_key:
            try:
                return self._videos_via_api(external_id, limit)
            except Exception as e:
                logger.warning(
                    "YouTube API videos fetch failed (%s); falling back to yt-dlp",
                    type(e).__name__,
                )
        return self._videos_via_ytdlp(external_id, limit)

    # ── YouTube Data API v3 path ───────────────────────────────────────────

    def _build_youtube_client(self):
        from googleapiclient.discovery import build  # type: ignore

        return build("youtube", "v3", developerKey=self.api_key, cache_discovery=False)

    def _meta_via_api(self, source_url: str) -> ChannelMeta:
        client = self._build_youtube_client()
        parsed = parse_channel_url(source_url)

        # Resolve to a YT channel id.
        channel_id: str | None = parsed.get("id")
        handle: str | None = parsed.get("handle")
        custom: str | None = parsed.get("custom")

        if not channel_id:
            # forHandle works for "@handle"; forUsername works for legacy /user/
            params: dict[str, Any] = {"part": "id,snippet,statistics"}
            if handle:
                params["forHandle"] = handle
            elif custom:
                params["forUsername"] = custom
            resp = client.channels().list(**params).execute()
            items = resp.get("items", [])
            if not items:
                raise LookupError(f"YouTube API found no channel for {source_url!r}")
            ch = items[0]
        else:
            resp = (
                client.channels()
                .list(part="id,snippet,statistics", id=channel_id)
                .execute()
            )
            items = resp.get("items", [])
            if not items:
                raise LookupError(f"YouTube API found no channel with id {channel_id!r}")
            ch = items[0]

        snippet = ch.get("snippet", {})
        stats = ch.get("statistics", {})
        thumb = (snippet.get("thumbnails") or {}).get("high") or {}

        return ChannelMeta(
            name=snippet.get("title") or "Unnamed channel",
            external_id=ch.get("id"),
            handle=snippet.get("customUrl") or handle,
            description=snippet.get("description"),
            thumbnail_url=thumb.get("url"),
            subscriber_count=int(stats["subscriberCount"]) if "subscriberCount" in stats else None,
            source_url=source_url,
        )

    def _videos_via_api(self, external_id: str, limit: int) -> list[VideoMeta]:
        client = self._build_youtube_client()
        # 1. Get the "uploads" playlist id (channel's full upload feed).
        resp = client.channels().list(part="contentDetails", id=external_id).execute()
        items = resp.get("items", [])
        if not items:
            return []
        uploads_id = items[0]["contentDetails"]["relatedPlaylists"]["uploads"]

        # 2. Page through playlistItems → video ids.
        video_ids: list[str] = []
        next_token: str | None = None
        while len(video_ids) < limit:
            params: dict[str, Any] = {
                "part": "contentDetails",
                "playlistId": uploads_id,
                "maxResults": min(50, limit - len(video_ids)),
            }
            if next_token:
                params["pageToken"] = next_token
            page = client.playlistItems().list(**params).execute()
            video_ids.extend(
                i["contentDetails"]["videoId"] for i in page.get("items", [])
            )
            next_token = page.get("nextPageToken")
            if not next_token:
                break

        # 3. Fetch full video details in batches of 50.
        out: list[VideoMeta] = []
        for i in range(0, len(video_ids), 50):
            batch = video_ids[i : i + 50]
            details = (
                client.videos()
                .list(part="snippet,contentDetails,statistics", id=",".join(batch))
                .execute()
            )
            for v in details.get("items", []):
                vid = v["id"]
                snip = v.get("snippet", {})
                stats = v.get("statistics", {})
                cd = v.get("contentDetails", {})
                source = f"https://www.youtube.com/watch?v={vid}"
                kind = "short" if _is_shorts_url(source) else "landscape"
                # YouTube API doesn't expose "is short" directly. Use duration:
                # videos <= 60s are usually shorts.
                dur = _iso8601_duration_to_seconds(cd.get("duration"))
                if dur is not None and dur <= 60:
                    kind = "short"
                    source = f"https://www.youtube.com/shorts/{vid}"
                thumbs = snip.get("thumbnails") or {}
                thumb_url = (thumbs.get("high") or thumbs.get("default") or {}).get("url")
                pub_at = snip.get("publishedAt")
                pub_dt = (
                    datetime.fromisoformat(pub_at.replace("Z", "+00:00"))
                    if pub_at
                    else None
                )
                out.append(
                    VideoMeta(
                        external_id=vid,
                        source_url=source,
                        title=snip.get("title") or "(untitled)",
                        kind=kind,
                        description=snip.get("description"),
                        thumbnail_url=thumb_url,
                        duration_seconds=dur,
                        view_count=int(stats["viewCount"]) if "viewCount" in stats else None,
                        published_at=pub_dt,
                    )
                )
        return out

    # ── yt-dlp fallback path ───────────────────────────────────────────────

    def _meta_via_ytdlp(self, source_url: str) -> ChannelMeta:
        import yt_dlp  # type: ignore

        with yt_dlp.YoutubeDL(
            {
                "quiet": True,
                "extract_flat": True,
                "skip_download": True,
                "ignoreerrors": False,
            }
        ) as ydl:
            info = ydl.extract_info(source_url, download=False)
        if info is None:
            raise LookupError(f"yt-dlp returned no info for {source_url!r}")

        return ChannelMeta(
            name=info.get("channel") or info.get("title") or "Unnamed channel",
            external_id=info.get("channel_id") or info.get("uploader_id"),
            handle=info.get("uploader_id") or info.get("channel_url", "").rsplit("/", 1)[-1] or None,
            description=info.get("description"),
            thumbnail_url=_first_thumb(info),
            subscriber_count=info.get("channel_follower_count"),
            source_url=source_url,
        )

    def _videos_via_ytdlp(self, external_id: str, limit: int) -> list[VideoMeta]:
        """Pull from BOTH /videos AND /shorts tabs, dedupe by id.

        YouTube splits long-form and shorts onto separate channel tabs;
        yt-dlp can't return both from a single URL.
        """
        import yt_dlp  # type: ignore

        if external_id.startswith("UC"):
            base = f"https://www.youtube.com/channel/{external_id}"
        elif external_id.startswith("@"):
            base = f"https://www.youtube.com/{external_id}"
        else:
            base = f"https://www.youtube.com/{external_id}"

        # Pull from BOTH tabs unconditionally so we always sample shorts even
        # when the videos tab alone would fill `limit`. Each tab is capped by
        # `playlistend`; we dedupe + truncate to `limit` at the end.
        per_tab = max(10, limit // 2 + 5)  # small buffer so the two tabs blend nicely
        opts = {
            "quiet": True,
            "extract_flat": True,
            "skip_download": True,
            "playlistend": per_tab,
            "ignoreerrors": True,
        }

        seen: set[str] = set()
        out: list[VideoMeta] = []
        for tab, default_kind in (("videos", "landscape"), ("shorts", "short")):
            try:
                with yt_dlp.YoutubeDL(opts) as ydl:
                    info = ydl.extract_info(f"{base}/{tab}", download=False)
            except Exception as e:
                logger.warning("yt-dlp %s/%s tab failed: %s", base, tab, e)
                continue
            if info is None:
                continue

            for entry in (info.get("entries") or []):
                if entry is None:
                    continue
                vid = entry.get("id") or ""
                if not vid or vid in seen:
                    continue
                seen.add(vid)

                entry_url = entry.get("url") or entry.get("webpage_url") or ""
                duration = entry.get("duration")
                kind = default_kind
                if _is_shorts_url(entry_url):
                    kind = "short"
                elif duration is not None and duration <= 60:
                    kind = "short"
                source = (
                    f"https://www.youtube.com/shorts/{vid}"
                    if kind == "short"
                    else f"https://www.youtube.com/watch?v={vid}"
                )
                ts = entry.get("timestamp")
                pub_dt = datetime.fromtimestamp(ts, tz=timezone.utc) if ts else None
                # yt-dlp's flat extraction often omits thumbnail data for
                # shorts. Fall back to YouTube's deterministic thumbnail URL —
                # `hqdefault.jpg` exists for every video id.
                thumb = _first_thumb(entry) or (
                    f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg" if vid else None
                )
                out.append(
                    VideoMeta(
                        external_id=vid,
                        source_url=source,
                        title=entry.get("title") or "(untitled)",
                        kind=kind,
                        description=entry.get("description"),
                        thumbnail_url=thumb,
                        duration_seconds=int(duration) if duration else None,
                        view_count=entry.get("view_count"),
                        published_at=pub_dt,
                    )
                )

        # Sort newest-first when published_at is available, then truncate.
        out.sort(key=lambda v: v.published_at or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
        return out[:limit]

# ─── helpers ───────────────────────────────────────────────────────────────────


def _first_thumb(info: dict) -> str | None:
    thumbs = info.get("thumbnails") or []
    if not thumbs:
        return info.get("thumbnail")
    # Prefer larger thumbs.
    sorted_thumbs = sorted(
        (t for t in thumbs if isinstance(t, dict)),
        key=lambda t: (t.get("width") or 0) * (t.get("height") or 0),
        reverse=True,
    )
    return sorted_thumbs[0].get("url") if sorted_thumbs else None


_DURATION_RE = re.compile(
    r"PT(?:(?P<h>\d+)H)?(?:(?P<m>\d+)M)?(?:(?P<s>\d+)S)?"
)


def _iso8601_duration_to_seconds(d: str | None) -> int | None:
    """YouTube API returns ISO-8601 durations like 'PT1M30S'."""
    if not d:
        return None
    m = _DURATION_RE.fullmatch(d)
    if not m:
        return None
    h = int(m.group("h") or 0)
    mi = int(m.group("m") or 0)
    s = int(m.group("s") or 0)
    return h * 3600 + mi * 60 + s
