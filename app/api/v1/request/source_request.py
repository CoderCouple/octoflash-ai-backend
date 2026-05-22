"""Source (input library) request models."""

from pydantic import BaseModel, Field, HttpUrl

from app.common.enum.source import SourcePlatform


class CreateSourceRequest(BaseModel):
    """Create a Source from a channel URL + (optionally) pre-fetched metadata.

    When the YouTube fetcher lands, the server will pull metadata itself; for
    now the client passes whatever it has and the row is saved verbatim.
    """

    source_url: HttpUrl
    platform: SourcePlatform = SourcePlatform.YOUTUBE
    name: str = Field(..., min_length=1, max_length=255)
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
