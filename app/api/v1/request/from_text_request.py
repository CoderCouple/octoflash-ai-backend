from pydantic import BaseModel, Field


class CreateProjectFromTextRequest(BaseModel):
    """Create a project from a free-form text description.

    Bypasses the AnalyzeProjectWorkflow entirely — no URL to download,
    transcribe, or describe. The text is treated as both the transcript and
    the manim brief, and the project is born `status='analyzed'` so it can
    go straight to /generate.
    """

    text: str = Field(
        ..., min_length=10, max_length=8000,
        description="Describe the video — content, tone, visual style, anything Claude needs.",
    )

    title: str | None = Field(
        default=None, max_length=255,
        description="Optional project title; defaults to a slug of the first line.",
    )

    target_duration: float | None = Field(
        default=None, ge=5, le=600,
        description="Target final-video duration in seconds. Defaults to 30s.",
    )
