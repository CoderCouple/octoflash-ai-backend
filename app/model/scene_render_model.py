"""SceneRender — one row per (scene, attempt) of the per-clip Manim render.

Wired by generate_clip_activity:
  * row inserted PENDING when the activity boots, before any work
  * flipped to RUNNING when the manim subprocess starts
  * SUCCEEDED on a clean exit; output_ref points at the Supabase ref
  * FAILED / TIMED_OUT on exhaustion of the internal fallback chain

A scene can have multiple SceneRender rows — one per internal attempt
(claude_voice, claude_voice_retry, claude_novoice, …). The FE renders
the lineage so the user can see "attempt 2 of 4 — fresh no-voice"
without having to dig into Temporal.

execution_log rows can be FK'd to this table (`scene_render_id`) so
the Manim subprocess's stderr stream is queryable per-clip.
"""

import uuid

from sqlalchemy import (
    TIMESTAMP,
    Column,
    ForeignKey,
    Integer,
    SmallInteger,
    Text,
    func,
)
from sqlalchemy import Enum as SAEnum

from app.common.enum.scene import RenderMethod, SceneRenderStatus
from app.db.base import Base


def generate_prefixed_uuid() -> str:
    return f"sr_{uuid.uuid4()}"


class SceneRender(Base):
    __tablename__ = "scene_render"

    id = Column(
        Text(), primary_key=True, default=generate_prefixed_uuid, nullable=False
    )

    scene_id = Column(
        Text(),
        ForeignKey("scene.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    workflow_execution_id = Column(
        Text(),
        ForeignKey("workflow_execution.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    attempt = Column(SmallInteger, nullable=False, default=1)
    status = Column(
        SAEnum(
            SceneRenderStatus,
            name="scene_render_status",
            create_type=False,
            values_callable=lambda e: [v.value for v in e],
        ),
        nullable=False,
        default=SceneRenderStatus.PENDING,
    )
    render_method = Column(
        SAEnum(
            RenderMethod,
            name="render_method_enum",
            create_type=False,
            values_callable=lambda e: [v.value for v in e],
        ),
        nullable=True,
    )

    started_at = Column(TIMESTAMP(timezone=True), nullable=True)
    completed_at = Column(TIMESTAMP(timezone=True), nullable=True)
    duration_ms = Column(Integer, nullable=True)

    # `supabase://renders/projects/<id>/clip_<scene_id>.mp4` or similar.
    # Resolved to a signed URL at the controller boundary.
    output_ref = Column(Text(), nullable=True)
    error_message = Column(Text(), nullable=True)

    temporal_activity_id = Column(Text(), nullable=True)
    temporal_attempt = Column(SmallInteger, nullable=True)

    created_at = Column(TIMESTAMP(timezone=True), nullable=False, default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), nullable=False, default=func.now())
