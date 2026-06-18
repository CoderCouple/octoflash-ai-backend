from pydantic import BaseModel, Field

from app.common.enum.scene import Orientation, Quality


class CreateProjectFromTextRequest(BaseModel):
    """Create a project from a free-form text brief.

    Bypasses the AnalyzeProjectWorkflow entirely — no URL to download,
    no captions to scrape, no frames to extract. The brief itself is what
    plan_clips, script_generator, and evaluator all read. Project is born
    `status='analyzed'` and a GenerateVideoWorkflow kicks immediately.

    The render options mirror `from_source_request.py` so a project
    created via either path lands in the same shape and the FE can
    show identical controls.
    """

    # Min 50 chars so plan_clips has enough material to split into N
    # clips. Below that the planner tends to produce 1-2 trivial clips
    # or repeat itself.
    brief: str = Field(
        ..., min_length=50, max_length=10_000,
        description="What the video should be about — content, tone, visual cues.",
    )

    title: str | None = Field(
        default=None, max_length=255,
        description="Optional project title; defaults to the first ~60 chars of brief.",
    )

    # Render options — every option is optional; omitted fields fall
    # back to the Project model's defaults (portrait, 720p, voiceover on).
    orientation: Orientation | None = None
    quality: Quality | None = None
    voiceover: bool | None = None
    voice_id: str | None = Field(default=None, max_length=64)
    voice_gender: str | None = Field(default=None, max_length=16)
    voice_accent: str | None = Field(default=None, max_length=32)
    target_duration: float | None = Field(default=None, ge=10, le=900)
    max_clips: int = Field(default=8, ge=1, le=20)
