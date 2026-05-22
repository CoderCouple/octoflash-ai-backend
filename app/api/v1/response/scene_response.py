from datetime import datetime

from pydantic import BaseModel, ConfigDict


class SceneResponse(BaseModel):
    """A scene (= clip) in a project's plan."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    orientation: str  # "portrait" | "landscape"
    n: int

    title: str | None = None
    prompt: str | None = None
    duration: float | None = None

    script_code: str | None = None
    script_code_hash: str | None = None
    script_file: str | None = None
    voice_id_override: str | None = None

    video_url: str | None = None
    render_method: str | None = None
    eval_score: int | None = None
    eval_feedback: str | None = None

    status: str
    created_at: datetime
    updated_at: datetime
