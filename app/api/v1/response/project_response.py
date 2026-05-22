from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.api.v1.response.scene_response import SceneResponse
from app.api.v1.response.workflow_response import WorkflowResponse


class ProjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    source_url: str | None = None
    user_id: str

    status: str  # ProjectStatus

    # Render options
    orientation: str
    quality: str
    voiceover: bool
    voice_id: str | None = None
    voice_gender: str | None = None
    voice_accent: str | None = None
    target_duration: float | None = None

    # Analyze output (editable by user)
    transcript: str | None = None
    description: str | None = None
    manim_prompt: str | None = None

    source_duration: float | None = None
    frames_dir: str | None = None
    final_portrait_video_url: str | None = None
    final_landscape_video_url: str | None = None

    is_deleted: bool
    created_at: datetime
    updated_at: datetime


class ProjectDetailResponse(ProjectResponse):
    """Project plus its scenes and workflow — what GET /projects/{id} returns."""

    scenes: list[SceneResponse] = []
    workflow: WorkflowResponse | None = None
