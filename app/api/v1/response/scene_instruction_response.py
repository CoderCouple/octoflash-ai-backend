from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class SceneInstructionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    scene_id: str
    instruction: str
    diff: dict[str, Any]
    applied_by: str | None = None
    applied_at: datetime
