from pydantic import BaseModel, Field


class CreateSceneRequest(BaseModel):
    """Add a scene/clip to a project. Most fields are populated by the planner;
    this is mainly for manual additions and edits."""

    title: str | None = Field(default=None, max_length=255)
    prompt: str | None = None  # creative direction for this clip
    duration: float | None = None
    n: int | None = None  # explicit ordering; defaults to next slot


class UpdateSceneRequest(BaseModel):
    title: str | None = None
    prompt: str | None = None
    duration: float | None = None
