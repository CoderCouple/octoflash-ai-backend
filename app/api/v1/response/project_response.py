from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.api.v1.response.scene_response import SceneResponse
from app.api.v1.response.workflow_response import WorkflowResponse


class ProjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    source_url: str | None = None
    owner_id: str | None = None
    is_deleted: bool
    created_at: datetime
    updated_at: datetime


class ProjectDetailResponse(ProjectResponse):
    """Project plus its scenes and workflow — what GET /projects/{id} returns."""

    scenes: list[SceneResponse] = []
    workflow: WorkflowResponse | None = None
