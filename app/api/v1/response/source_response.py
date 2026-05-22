"""Source (input library) response models."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.common.enum.source import SourcePlatform, SourceVideoKind


class SourceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    platform: SourcePlatform
    source_url: str
    external_id: str | None = None
    handle: str | None = None
    name: str
    description: str | None = None
    thumbnail_url: str | None = None
    subscriber_count: int | None = None
    accent_color: str | None = None
    last_synced_at: datetime | None = None
    is_deleted: bool
    created_at: datetime
    updated_at: datetime


class SourceVideoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    source_id: str
    external_id: str
    source_url: str
    title: str
    description: str | None = None
    thumbnail_url: str | None = None
    kind: SourceVideoKind
    duration_seconds: int | None = None
    view_count: int | None = None
    published_at: datetime | None = None
    fetched_at: datetime
    created_at: datetime


class SourceDetailResponse(SourceResponse):
    """Source + a slice of its videos."""

    videos: list[SourceVideoResponse] = []
