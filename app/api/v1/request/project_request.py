from pydantic import BaseModel, Field


class CreateProjectRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    source_url: str | None = None
    prompt: str | None = None  # freeform entry — passed to planner


class UpdateProjectRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    source_url: str | None = None
