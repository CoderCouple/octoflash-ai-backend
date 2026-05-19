"""
Audit log of natural-language instructions applied to a scene.

One row per `POST /scenes/{id}/instruct` call. The applied diff is stored
verbatim so the history is replayable and reviewable even after the scene's
`extra_steps` has been collapsed or further modified.
"""

import uuid

from sqlalchemy import TIMESTAMP, Column, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB

from app.db.base import Base


def generate_prefixed_uuid() -> str:
    return f"sins_{uuid.uuid4()}"


class SceneInstruction(Base):
    __tablename__ = "scene_instruction"

    id = Column(String(), primary_key=True, default=generate_prefixed_uuid, nullable=False)
    scene_id = Column(String(), ForeignKey("scene.id"), nullable=False, index=True)

    instruction = Column(Text(), nullable=False)
    """The user's natural-language input, verbatim."""

    diff = Column(JSONB, nullable=False, default=dict)
    """What this instruction did, captured for audit/display:
        {
          "extra_steps_before": [...],
          "extra_steps_after":  [...],
          "reasoning":          "...",   # from the planner LLM
          "warnings":           [...],
        }
    """

    applied_by = Column(String(), nullable=True)
    applied_at = Column(TIMESTAMP(timezone=True), default=func.now(), nullable=False)
