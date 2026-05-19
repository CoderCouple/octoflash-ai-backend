"""Channel API — pasted URL → metadata + recent videos."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.tags import Tags
from app.api.v1.request.channel_request import CreateChannelRequest, SyncChannelRequest
from app.api.v1.response.base_response import BaseResponse, success_response
from app.api.v1.response.channel_response import (
    ChannelDetailResponse,
    ChannelResponse,
    ChannelVideoResponse,
    SyncChannelResponse,
)
from app.common.pagination import PaginatedResponse
from app.db.session import get_db
from app.service.channel_service import ChannelService

router = APIRouter(tags=[Tags.Channel])


def get_channel_service(db: AsyncSession = Depends(get_db)) -> ChannelService:
    return ChannelService(db)


@router.post("/channels", response_model=BaseResponse[ChannelResponse], status_code=201)
async def create_channel(
    body: CreateChannelRequest,
    service: ChannelService = Depends(get_channel_service),
):
    """Paste a channel URL → resolve metadata (sync, ~1-3s) → persist.

    De-dupes by `(platform, external_id)` — re-pasting an existing channel
    refreshes its metadata and returns the existing row.
    Does NOT fetch videos; call POST /channels/{id}/sync to populate them.
    """
    result = await service.create_from_url(str(body.source_url))
    return success_response(result, "Channel created", 201)


@router.get(
    "/channels", response_model=BaseResponse[PaginatedResponse[ChannelResponse]]
)
async def list_channels(
    owner_id: str | None = Query(default=None),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    service: ChannelService = Depends(get_channel_service),
):
    channels, total = await service.list_channels(owner_id, offset, limit)
    page = PaginatedResponse(items=channels, total=total, offset=offset, limit=limit)
    return success_response(page, "Channels fetched")


@router.get(
    "/channels/{channel_id}", response_model=BaseResponse[ChannelDetailResponse]
)
async def get_channel(
    channel_id: str,
    service: ChannelService = Depends(get_channel_service),
):
    """Channel + its most recent videos (up to 100)."""
    result = await service.get_detail(channel_id)
    return success_response(result, "Channel fetched")


@router.get(
    "/channels/{channel_id}/videos",
    response_model=BaseResponse[PaginatedResponse[ChannelVideoResponse]],
)
async def list_channel_videos(
    channel_id: str,
    kind: str | None = Query(default=None, description="Filter: 'short' or 'landscape'"),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    service: ChannelService = Depends(get_channel_service),
):
    videos, total = await service.list_videos(channel_id, kind, offset, limit)
    page = PaginatedResponse(items=videos, total=total, offset=offset, limit=limit)
    return success_response(page, "Videos fetched")


@router.post(
    "/channels/{channel_id}/sync",
    response_model=BaseResponse[SyncChannelResponse],
)
async def sync_channel(
    channel_id: str,
    body: SyncChannelRequest,
    service: ChannelService = Depends(get_channel_service),
):
    """Re-fetch recent videos from YouTube and upsert into the DB.

    Synchronous — request holds open for the duration (~2-30s depending on
    fetcher + channel size). If this gets too slow at scale, swap to
    FastAPI BackgroundTasks (no new infra needed).
    """
    count = await service.sync(channel_id, body.max_videos)
    return success_response(
        SyncChannelResponse(channel_id=channel_id, videos_upserted=count),
        f"Synced {count} videos",
    )


@router.delete("/channels/{channel_id}", response_model=BaseResponse)
async def delete_channel(
    channel_id: str,
    service: ChannelService = Depends(get_channel_service),
):
    await service.delete(channel_id)
    return success_response(None, "Channel deleted")
