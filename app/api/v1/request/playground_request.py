from pydantic import BaseModel, Field


class PlaygroundRenderRequest(BaseModel):
    code: str = Field(..., min_length=1, max_length=32_000)
    scene_name: str | None = Field(default=None, max_length=128)
    quality: str = Field(default="720p")
