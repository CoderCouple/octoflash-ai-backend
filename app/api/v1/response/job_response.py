from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class JobResponse(BaseModel):
    """Standard job-status shape — matches the frontend's polled contract."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    kind: str
    project_id: str | None = None
    scene_id: str | None = None
    status: str  # queued | running | done | failed
    progress: int  # 0-100
    logs: list[Any] = []
    output_url: str | None = None
    workflow_id: str | None = None
    run_id: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    created_at: datetime
