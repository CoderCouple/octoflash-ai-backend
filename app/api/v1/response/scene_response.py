from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class SceneResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    n: int
    title: str | None = None
    template: str
    params: dict[str, Any]
    prompt: str | None = None
    duration: float | None = None
    style: str | None = None
    motion: str | None = None
    status: str
    selected_variation_id: str | None = None
    extra_steps: list[dict[str, Any]] = []
    mode: str = "structured"
    created_at: datetime
    updated_at: datetime
