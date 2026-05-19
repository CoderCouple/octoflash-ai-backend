from pydantic import BaseModel


class PreviewRequest(BaseModel):
    """Low-quality stitch along a chosen path."""

    end_node_id: str | None = None  # which end to render to; defaults to the project's first end


class ExportRequest(BaseModel):
    """Full-quality stitch + encode."""

    end_node_id: str | None = None
    format: str = "mp4"  # mp4 | mov
