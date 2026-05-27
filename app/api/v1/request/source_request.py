"""Source (input library) request models."""

from pydantic import BaseModel, Field, HttpUrl

from app.common.enum.source import SourcePlatform


class CreateSourceRequest(BaseModel):
    """Create a Source from a channel URL.

    Only `source_url` is required — the server resolves the channel via the
    platform's fetcher (yt-dlp for YouTube) and fills in name / handle /
    external_id / thumbnail / subscriber count. Any field the client
    explicitly provides overrides the fetched value.
    """

    source_url: HttpUrl
    platform: SourcePlatform = SourcePlatform.YOUTUBE
    name: str | None = Field(default=None, min_length=1, max_length=255)
    external_id: str | None = Field(default=None, max_length=128)
    handle: str | None = Field(default=None, max_length=128)
    description: str | None = None
    thumbnail_url: HttpUrl | None = None
    subscriber_count: int | None = Field(default=None, ge=0)
    accent_color: str | None = Field(default=None, max_length=16)


class UpdateSourceRequest(BaseModel):
    """Partial update — every field optional."""

    name: str | None = Field(default=None, min_length=1, max_length=255)
    handle: str | None = Field(default=None, max_length=128)
    description: str | None = None
    thumbnail_url: HttpUrl | None = None
    subscriber_count: int | None = Field(default=None, ge=0)
    accent_color: str | None = Field(default=None, max_length=16)
