from pydantic import BaseModel, Field, HttpUrl


class CreateProjectFromSourceRequest(BaseModel):
    """Create a project from a single source URL.

    Source types (auto-detected from URL):
      - YouTube long-form (/watch?v=, /v/, youtu.be/, /embed/)
      - YouTube shorts (/shorts/<id>)
      - Medium articles (medium.com/...)
      - Substack articles (*.substack.com/...)

    User-facing render options (orientation, voice, quality, target_duration)
    are set on the Project after creation, before kicking off the generate
    workflow.
    """

    source_url: HttpUrl

    title: str | None = Field(
        default=None, max_length=255,
        description="Optional project title; defaults to the source's title.",
    )
