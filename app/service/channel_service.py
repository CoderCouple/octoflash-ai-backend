"""
ChannelService — create channels from a URL, list, sync, delete.

YouTube fetching is sync (network-bound, ~1-30s). FastAPI handles the request
holding open; we wrap the blocking yt-dlp / google-api calls in
`asyncio.to_thread(...)` so the event loop stays responsive.

No Temporal here — channel sync is short-lived, sequential, and cheap. Use
Temporal only for the heavy render/concat work where its durability earns
its keep.
"""

from __future__ import annotations

import asyncio
from dataclasses import asdict

from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.response.channel_response import (
    ChannelDetailResponse,
    ChannelResponse,
    ChannelVideoResponse,
)
from app.common.exceptions import EntityNotFoundError
from app.db.repository.channel_repository import ChannelRepository
from app.db.repository.channel_video_repository import ChannelVideoRepository
from app.model.channel_model import Channel
from app.service.youtube_fetcher_service import YouTubeFetcherService


class ChannelService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.channel_repo = ChannelRepository(db)
        self.video_repo = ChannelVideoRepository(db)
        self.fetcher = YouTubeFetcherService()

    async def create_from_url(
        self, source_url: str, owner_id: str | None = None
    ) -> ChannelResponse:
        """Resolve URL → channel metadata → insert (or de-dupe) → return.

        Does NOT fetch videos. Caller hits POST /channels/{id}/sync (or the
        FE just calls it right after this).
        """
        meta = await asyncio.to_thread(self.fetcher.fetch_channel_metadata, source_url)

        # De-dupe: if this YT channel id is already in our DB, reuse it.
        if meta.external_id:
            existing = await self.channel_repo.get_by_external_id("youtube", meta.external_id)
            if existing:
                # Refresh mutable metadata so the FE sees current numbers.
                existing.name = meta.name
                existing.handle = meta.handle or existing.handle
                existing.description = meta.description
                existing.thumbnail_url = meta.thumbnail_url
                existing.subscriber_count = meta.subscriber_count
                await self.channel_repo.update(existing)
                return ChannelResponse.model_validate(existing)

        channel = Channel(
            platform="youtube",
            source_url=source_url,
            external_id=meta.external_id,
            handle=meta.handle,
            name=meta.name,
            description=meta.description,
            thumbnail_url=meta.thumbnail_url,
            subscriber_count=meta.subscriber_count,
            owner_id=owner_id,
        )
        channel = await self.channel_repo.create(channel)
        return ChannelResponse.model_validate(channel)

    async def list_channels(
        self, owner_id: str | None = None, offset: int = 0, limit: int = 50
    ) -> tuple[list[ChannelResponse], int]:
        rows, total = await self.channel_repo.list_all(owner_id, offset, limit)
        return [ChannelResponse.model_validate(r) for r in rows], total

    async def get_detail(self, channel_id: str) -> ChannelDetailResponse:
        channel = await self.channel_repo.get_by_id(channel_id)
        if not channel:
            raise EntityNotFoundError("Channel", channel_id)

        videos, _total = await self.video_repo.list_by_channel(channel_id, limit=100)
        return ChannelDetailResponse(
            **ChannelResponse.model_validate(channel).model_dump(),
            videos=[ChannelVideoResponse.model_validate(v) for v in videos],
        )

    async def list_videos(
        self,
        channel_id: str,
        kind: str | None = None,
        offset: int = 0,
        limit: int = 100,
    ) -> tuple[list[ChannelVideoResponse], int]:
        channel = await self.channel_repo.get_by_id(channel_id)
        if not channel:
            raise EntityNotFoundError("Channel", channel_id)
        videos, total = await self.video_repo.list_by_channel(channel_id, kind, offset, limit)
        return [ChannelVideoResponse.model_validate(v) for v in videos], total

    async def sync(self, channel_id: str, max_videos: int | None = None) -> int:
        """Fetch recent videos from YouTube → upsert. Returns count touched."""
        from datetime import datetime, timezone

        channel = await self.channel_repo.get_by_id(channel_id)
        if not channel:
            raise EntityNotFoundError("Channel", channel_id)
        if not channel.external_id:
            raise EntityNotFoundError(
                "Channel.external_id", channel_id
            )  # malformed — never resolved YT id

        videos_meta = await asyncio.to_thread(
            self.fetcher.fetch_channel_videos, channel.external_id, max_videos
        )
        touched = await self.video_repo.upsert_many(
            channel_id, [asdict(v) for v in videos_meta]
        )

        channel.last_synced_at = datetime.now(timezone.utc)
        await self.channel_repo.update(channel)
        return touched

    async def delete(self, channel_id: str) -> None:
        channel = await self.channel_repo.get_by_id(channel_id)
        if not channel:
            raise EntityNotFoundError("Channel", channel_id)
        await self.channel_repo.soft_delete(channel)
