from typing import Literal

from pydantic import BaseModel, Field, HttpUrl, model_validator

from app.common.enum.scene import Orientation, Quality


# Per-frame payload bound. Base64 inflates raw bytes by ~4/3, so a 2 MB
# JPEG encodes to ~2.7 MB of base64 (~37 chars/KB). Cap each field a hair
# above 3 MB to allow a tiny data-URL prefix while keeping a single
# request's frame array under ~75 MB worst case (24 × 3 MB). Anything
# larger should be downscaled by the client before upload.
_MAX_FRAME_FIELD_LEN = 3 * 1024 * 1024


class LocalIngestFrameRequest(BaseModel):
    """A browser-captured source frame.

    The extension should prefer JPEG data URLs from canvas capture. When canvas
    capture is blocked, it can send a JPEG-encoded poster/thumbnail instead and
    mark `source="poster"`.
    """

    image_base64: str | None = Field(default=None, min_length=1, max_length=_MAX_FRAME_FIELD_LEN)
    data_url: str | None = Field(default=None, min_length=1, max_length=_MAX_FRAME_FIELD_LEN)
    captured_at: float | None = Field(default=None, ge=0)
    source: Literal["canvas", "poster", "thumbnail"] = "canvas"

    @model_validator(mode="after")
    def require_image_payload(self) -> "LocalIngestFrameRequest":
        if not self.image_base64 and not self.data_url:
            raise ValueError("frame must include image_base64 or data_url")
        return self


class CreateProjectFromLocalIngestRequest(BaseModel):
    """Create an analyzed project from browser-side YouTube ingest.

    This path avoids server-side YouTube downloads. The client/extension sends
    transcript text plus a small set of sampled JPEG frames captured while the
    user is playing the video in their browser session.
    """

    source_url: HttpUrl
    title: str | None = Field(default=None, max_length=255)

    transcript: str = Field(default="", max_length=250_000)
    source_duration: float | None = Field(default=None, ge=0, le=7200)
    frames: list[LocalIngestFrameRequest] = Field(default_factory=list, max_length=24)
    description: str | None = Field(
        default=None,
        max_length=50_000,
        description="Optional client-provided fallback visual description.",
    )

    orientation: Orientation | None = None
    quality: Quality | None = None
    voiceover: bool | None = None
    voice_id: str | None = Field(default=None, max_length=64)
    voice_gender: str | None = Field(default=None, max_length=16)
    voice_accent: str | None = Field(default=None, max_length=32)
    target_duration: float | None = Field(default=None, ge=10, le=900)
