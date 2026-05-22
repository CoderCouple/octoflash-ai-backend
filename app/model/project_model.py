"""Project — a user's video project. One source URL → one final video.

A project is a generic container; for v1 it carries the video-domain columns
directly (brief, render options, final mp4). Future child entities (e.g.
asset collections, publication configs) get their own 1:N tables hanging off
project.id rather than column sprawl here.

`owner_id` was renamed to `user_id` and is now a real FK → user.id.
"""

import uuid

from sqlalchemy import TIMESTAMP, Boolean, Column, Float, ForeignKey, String, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy import func

from app.common.enum.scene import Orientation, ProjectStatus, Quality
from app.db.base import Base


def generate_prefixed_uuid() -> str:
    return f"prj_{uuid.uuid4()}"


class Project(Base):
    __tablename__ = "project"

    id = Column(String(), primary_key=True, default=generate_prefixed_uuid, nullable=False)
    user_id = Column(String(), ForeignKey("user.id"), nullable=False, index=True)
    # Tenancy — nullable while the existing routes are migrated to require
    # auth. New rows created via authenticated paths must populate both.
    org_id = Column(String(), nullable=True, index=True)
    workspace_id = Column(String(), nullable=True, index=True)
    title = Column(String(255), nullable=False)
    source_url = Column(Text(), nullable=True)

    status = Column(
        SAEnum(
            ProjectStatus,
            name="project_status_enum",
            create_type=False,
            values_callable=lambda e: [v.value for v in e],
        ),
        nullable=False,
        default=ProjectStatus.QUEUED,
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
    quality = Column(
        SAEnum(
            Quality,
            name="quality_enum",
            create_type=False,
            values_callable=lambda e: [v.value for v in e],
        ),
        nullable=False,
        default=Quality.MEDIUM,
    )
    voiceover = Column(Boolean, nullable=False, default=True)
    voice_id = Column(String(64), nullable=True)
    voice_gender = Column(String(16), nullable=True)
    voice_accent = Column(String(32), nullable=True)
    target_duration = Column(Float, nullable=True)

    transcript = Column(Text(), nullable=True)
    description = Column(Text(), nullable=True)
    manim_prompt = Column(Text(), nullable=True)

    source_duration = Column(Float, nullable=True)
    frames_dir = Column(Text(), nullable=True)
    final_portrait_video_url = Column(Text(), nullable=True)
    final_landscape_video_url = Column(Text(), nullable=True)

    is_deleted = Column(Boolean, nullable=False, default=False)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), nullable=False, default=func.now())
