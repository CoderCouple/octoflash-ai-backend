from pydantic import BaseModel


class PlaygroundPresetResponse(BaseModel):
    id: str
    label: str
    duration: str
    preview: str
    code: str


class PlaygroundRenderResponse(BaseModel):
    render_id: str
    video_url: str
    scene_class: str
    quality: str
    took_ms: int
    log_lines: list[str]
    sandbox_mode: str
