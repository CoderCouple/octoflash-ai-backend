"""Scene — a clip in a Project's plan. One Scene = one Manim render = one MP4 segment.

`status` and `render_method` switched to native PG enums (matched against the
Python str-Enum classes in app.common.enum.scene).
"""

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
)
from sqlalchemy import Enum as SAEnum
from sqlalchemy import func

from app.common.enum.scene import Orientation, RenderMethod, SceneStatus
from app.db.base import Base


def generate_prefixed_uuid() -> str:
    return f"scn_{uuid.uuid4()}"


class Scene(Base):
    __tablename__ = "scene"
    __table_args__ = (
        UniqueConstraint(
            "project_id", "orientation", "n", name="uq_scene_project_orientation_n"
        ),
    )

    id = Column(String(), primary_key=True, default=generate_prefixed_uuid, nullable=False)
    project_id = Column(
        String(),
        ForeignKey("project.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    orientation = Column(
        SAEnum(
            Orientation,
            name="orientation_enum",
            create_type=False,
            values_callable=lambda e: [v.value for v in e],
        ),
        nullable=False,
        default=Orientation.PORTRAIT,
    )
    n = Column(Integer, nullable=False)

    title = Column(String(255), nullable=True)
    prompt = Column(Text(), nullable=True)
    duration = Column(Float, nullable=True)

    script_code = Column(Text(), nullable=True)
    script_code_hash = Column(String(64), nullable=True, index=True)
    script_file = Column(Text(), nullable=True)
    voice_id_override = Column(String(64), nullable=True)

    video_url = Column(Text(), nullable=True)
    render_method = Column(
        SAEnum(
            RenderMethod,
            name="render_method_enum",
            create_type=False,
            values_callable=lambda e: [v.value for v in e],
        ),
        nullable=True,
    )
    eval_score = Column(Integer, nullable=True)
    eval_feedback = Column(Text(), nullable=True)

    status = Column(
        SAEnum(
            SceneStatus,
            name="scene_status_enum",
            create_type=False,
            values_callable=lambda e: [v.value for v in e],
        ),
        nullable=False,
        default=SceneStatus.DRAFT,
    )

    created_at = Column(TIMESTAMP(timezone=True), nullable=False, default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), nullable=False, default=func.now())
