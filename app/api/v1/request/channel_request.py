from pydantic import BaseModel, Field, HttpUrl


class CreateChannelRequest(BaseModel):
    source_url: HttpUrl = Field(
        ..., description="Channel URL: /channel/UCxxx, /@handle, /c/name, or /user/name."
    )


class SyncChannelRequest(BaseModel):
    max_videos: int | None = Field(
        default=None, ge=1, le=500,
        description="Cap recent-videos fetch (defaults to channel_sync_max_videos setting).",
    )
