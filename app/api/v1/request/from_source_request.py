from pydantic import BaseModel, Field, HttpUrl

from app.common.enum.scene import Orientation, Quality


class CreateProjectFromSourceRequest(BaseModel):
    """Create a project from a single source URL.

    Source types (auto-detected from URL):
      - YouTube long-form (/watch?v=, /v/, youtu.be/, /embed/)
      - YouTube shorts (/shorts/<id>)
      - Medium articles (medium.com/...)
      - Substack articles (*.substack.com/...)

    Render options can be stamped at creation time so the user doesn't
    have to revisit the project before the first Generate. Every option
    is optional — omitted fields fall back to the Project model's
    defaults (portrait, 720p, voiceover on, no target duration).
    """

    source_url: HttpUrl

    title: str | None = Field(
        default=None, max_length=255,
        description="Optional project title; defaults to the source's title.",
    )

    # Render options — applied to the Project row immediately after
    # creation. Generate workflows read them off the row, so changing
    # them later via PATCH /projects/{id} also works.
    orientation: Orientation | None = None
    quality: Quality | None = None
    voiceover: bool | None = None
    voice_id: str | None = Field(default=None, max_length=64)
    voice_gender: str | None = Field(default=None, max_length=16)
    voice_accent: str | None = Field(default=None, max_length=32)
    target_duration: float | None = Field(default=None, ge=10, le=900)
