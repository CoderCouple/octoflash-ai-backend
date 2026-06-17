"""SourceService — CRUD over the input library.

Source = a creator channel the user has saved as input material (e.g. a
YouTube channel they pull source content FROM). Distinct from Target,
which is publishing destinations.
"""

import asyncio
import logging
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.request.source_request import CreateSourceRequest, UpdateSourceRequest
from app.api.v1.response.source_response import (
    SourceDetailResponse,
    SourceResponse,
    SourceVideoResponse,
)
from app.common.enum.source import SourcePlatform, SourceVideoKind, detect_platform
from app.common.exceptions import EntityNotFoundError
from app.db.repository.source_repository import SourceRepository
from app.db.repository.source_video_repository import SourceVideoRepository
from app.model.source_model import Source
from app.model.source_video_model import SourceVideo, generate_prefixed_uuid as gen_srcv_id
from app.service.youtube_fetcher_service import get_youtube_fetcher
from app.settings import settings

log = logging.getLogger(__name__)


class SourceService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.source_repo = SourceRepository(db)
        self.video_repo = SourceVideoRepository(db)

    async def list(
        self, user_id: str | None = None, offset: int = 0, limit: int = 50
    ) -> tuple[list[SourceResponse], int]:
        sources, total = await self.source_repo.list_for_user(
            user_id or settings.default_user_id, offset, limit
        )
        return [SourceResponse.model_validate(s) for s in sources], total

    async def get_detail(
        self, source_id: str, user_id: str, video_limit: int = 50
    ) -> SourceDetailResponse:
        source = await self.source_repo.get_by_id(source_id)
        if source is None or source.user_id != user_id:
            # 404 not 403 — don't leak that the row exists under a different user.
            raise EntityNotFoundError("Source", source_id)
        videos = await self.video_repo.list_for_source(source_id, 0, video_limit)
        return SourceDetailResponse(
            **SourceResponse.model_validate(source).model_dump(),
            videos=[SourceVideoResponse.model_validate(v) for v in videos],
        )

    async def create(
        self, body: CreateSourceRequest, user_id: str | None = None
    ) -> SourceResponse:
        """Create (or re-use) a Source from just a URL.

        Resolves the URL via the platform fetcher (yt-dlp for YouTube),
        merges the fetched metadata with any fields the client supplied
        (client wins for non-empty overrides), and de-dupes by
        (user_id, platform, external_id).
        """
        owner = user_id or settings.default_user_id
        source_url = str(body.source_url)

        # Auto-detect platform from URL host. Client may override.
        platform = body.platform or detect_platform(source_url)
        if platform is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Couldn't detect a supported platform from {source_url!r}. "
                    "Supported: youtube, instagram, tiktok, x, linkedin. "
                    "Pass `platform` explicitly if your URL uses a non-standard host."
                ),
            )

        # Resolve channel metadata server-side. yt-dlp is blocking → to_thread.
        fetched: dict = {}
        if platform == SourcePlatform.YOUTUBE:
            try:
                fetched = await asyncio.to_thread(
                    get_youtube_fetcher().fetch_channel_metadata, source_url,
                )
            except Exception as e:  # noqa: BLE001
                log.warning("SourceService.create: fetcher failed for %s: %s", source_url, e)
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Could not resolve {platform.value} URL: {e}",
                ) from e
        else:
            # IG / TikTok / etc — no fetcher wired yet. Require the client
            # to supply at least a name (so we don't silently store an
            # un-named row).
            if not body.name:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        f"{platform.value} fetcher not yet wired — "
                        "pass `name` explicitly until OAuth-backed ingest lands."
                    ),
                )

        # Client-supplied values win over fetched ones; for everything else
        # fall back to the fetcher payload.
        external_id = body.external_id or fetched.get("external_id")
        name = body.name or fetched.get("title") or "Untitled source"

        # De-dupe by (user, platform, channel-id) so re-pasting the same URL
        # refreshes the row instead of creating a duplicate.
        if external_id:
            existing = await self.source_repo.get_by_platform_external_id(
                owner, platform.value, external_id,
            )
            if existing is not None:
                existing.source_url = source_url
                if name:
                    existing.name = name
                if body.handle or fetched.get("handle"):
                    existing.handle = body.handle or fetched.get("handle")
                desc = body.description or fetched.get("description")
                if desc:
                    existing.description = desc
                thumb = (
                    str(body.thumbnail_url) if body.thumbnail_url
                    else fetched.get("thumbnail_url")
                )
                if thumb:
                    existing.thumbnail_url = thumb
                subs = (
                    body.subscriber_count if body.subscriber_count is not None
                    else fetched.get("subscriber_count")
                )
                if subs is not None:
                    existing.subscriber_count = subs
                existing = await self.source_repo.update(existing)
                return SourceResponse.model_validate(existing)

        source = Source(
            user_id=owner,
            platform=platform,
            source_url=source_url,
            external_id=external_id,
            handle=body.handle or fetched.get("handle"),
            name=name,
            description=body.description or fetched.get("description"),
            thumbnail_url=(
                str(body.thumbnail_url) if body.thumbnail_url
                else fetched.get("thumbnail_url")
            ),
            subscriber_count=(
                body.subscriber_count if body.subscriber_count is not None
                else fetched.get("subscriber_count")
            ),
            accent_color=body.accent_color,
        )
        source = await self.source_repo.create(source)
        return SourceResponse.model_validate(source)

    async def update(
        self, source_id: str, user_id: str, body: UpdateSourceRequest
    ) -> SourceResponse:
        source = await self.source_repo.get_by_id(source_id)
        if source is None or source.user_id != user_id:
            raise EntityNotFoundError("Source", source_id)
        for field in ("name", "handle", "description", "subscriber_count", "accent_color"):
            value = getattr(body, field)
            if value is not None:
                setattr(source, field, value)
        if body.thumbnail_url is not None:
            source.thumbnail_url = str(body.thumbnail_url)
        source = await self.source_repo.update(source)
        return SourceResponse.model_validate(source)

    async def delete(self, source_id: str, user_id: str) -> None:
        source = await self.source_repo.get_by_id(source_id)
        if source is None or source.user_id != user_id:
            raise EntityNotFoundError("Source", source_id)
        await self.source_repo.soft_delete(source)

    async def sync_videos(self, source_id: str, user_id: str) -> int:
        """Fetch the latest videos for this source and upsert them.

        yt-dlp runs synchronously, so we offload to a thread. Upserts go
        through SourceVideoRepository.upsert_many (ON CONFLICT (source_id,
        external_id) DO UPDATE), so re-syncs refresh title / view counts
        without duplicating rows. Returns the number of videos written.

        Only YouTube is supported today (and it's the only platform enum
        value); other platforms will land via the same dispatcher when added.
        """
        source = await self.source_repo.get_by_id(source_id)
        if source is None or source.user_id != user_id:
            raise EntityNotFoundError("Source", source_id)

        platform = (
            source.platform.value if hasattr(source.platform, "value") else source.platform
        )
        if platform != "youtube":
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail=f"Sync not implemented for platform {platform!r}.",
            )

        fetcher = get_youtube_fetcher()
        # Prefer the channel id (stable across handle renames); fall back to
        # the URL the user pasted.
        target = source.external_id or source.source_url
        max_videos = settings.channel_sync_max_videos or 50

        try:
            raw_videos = await asyncio.to_thread(
                fetcher.fetch_channel_videos, target, max_videos,
            )
        except RuntimeError as e:
            log.warning("sync_videos: fetcher failed for source=%s: %s", source_id, e)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"YouTube fetch failed: {e}",
            )

        models = [
            SourceVideo(
                id=gen_srcv_id(),
                source_id=source.id,
                external_id=v["external_id"],
                source_url=v["source_url"],
                title=v["title"],
                description=v.get("description"),
                thumbnail_url=v.get("thumbnail_url"),
                kind=SourceVideoKind(v.get("kind") or "landscape"),
                duration_seconds=v.get("duration_seconds"),
                view_count=v.get("view_count"),
                published_at=v.get("published_at"),
            )
            for v in raw_videos
            if v.get("external_id")
        ]
        written = await self.video_repo.upsert_many(models)

        source.last_synced_at = datetime.now(timezone.utc)
        await self.source_repo.update(source)
        await self.db.commit()
        log.info(
            "sync_videos: source=%s wrote=%d (fetched=%d) target=%s",
            source_id, written, len(raw_videos), target,
        )
        return written
