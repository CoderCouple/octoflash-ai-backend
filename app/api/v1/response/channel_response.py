from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ChannelResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    platform: str
    source_url: str
    external_id: str | None = None
    handle: str | None = None
    name: str
    description: str | None = None
    thumbnail_url: str | None = None
    subscriber_count: int | None = None
    accent_color: str | None = None
    last_synced_at: datetime | None = None
    owner_id: str | None = None
    is_deleted: bool
    created_at: datetime
    updated_at: datetime


class ChannelVideoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    channel_id: str
    external_id: str
    source_url: str
    title: str
    description: str | None = None
    thumbnail_url: str | None = None
    kind: str  # "short" | "landscape"
    duration_seconds: int | None = None
    view_count: int | None = None
    published_at: datetime | None = None
    fetched_at: datetime
    created_at: datetime


class ChannelDetailResponse(ChannelResponse):
    """Channel + a slice of its most recent videos."""

    videos: list[ChannelVideoResponse] = []


class SyncChannelResponse(BaseModel):
    channel_id: str
    videos_upserted: int
