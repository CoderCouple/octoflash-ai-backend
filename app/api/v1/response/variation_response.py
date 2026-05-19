from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class VariationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    scene_id: str
    params_snapshot: dict[str, Any]
    video_url: str | None = None
    audio_url: str | None = None
    duration: float | None = None
    frame_count: int | None = None
    file_size: int | None = None
    status: str
    rendered_at: datetime | None = None
    created_at: datetime
