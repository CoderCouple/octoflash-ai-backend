import uuid

from sqlalchemy import (
    TIMESTAMP,
    Column,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB

from app.db.base import Base


def generate_prefixed_uuid() -> str:
    return f"scn_{uuid.uuid4()}"


class Scene(Base):
    __tablename__ = "scene"
    __table_args__ = (
        UniqueConstraint("project_id", "n", name="uq_scene_project_n"),
    )

    id = Column(String(), primary_key=True, default=generate_prefixed_uuid, nullable=False)
    project_id = Column(String(), ForeignKey("project.id"), nullable=False, index=True)
    n = Column(Integer, nullable=False)  # order within project
    title = Column(String(255), nullable=True)
    template = Column(String(64), nullable=False)  # template id, e.g. "title_reveal"
    params = Column(JSONB, nullable=False, default=dict)
    prompt = Column(Text(), nullable=True)
    duration = Column(Float, nullable=True)  # seconds; None = template default
    style = Column(String(32), nullable=True)  # StylePreset value
    motion = Column(String(32), nullable=True)
    status = Column(String(16), nullable=False, default="draft")  # SceneStatus
    selected_variation_id = Column(String(), nullable=True)

    # NL editing divergence — populated only when the user has applied an instruction.
    # Merged with the template's steps at render time by TemplateRenderer.
    extra_steps = Column(JSONB, nullable=False, default=list)
    # "structured" = scene == (template, params); "advanced" = extra_steps non-empty.
    mode = Column(String(16), nullable=False, default="structured")

    created_at = Column(TIMESTAMP(timezone=True), default=func.now(), nullable=False)
    updated_at = Column(TIMESTAMP(timezone=True), default=func.now(), nullable=False)
