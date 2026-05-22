"""WorkflowNodeInstance — per-canvas node placement.

Projection of the nodes in `workflow.definition` JSONB. Maintained on save so
queries like "list scene nodes in this workflow" don't need JSONB parsing.
`scene_id` is set only when `type_id` points at the 'scene' node type.
"""

import uuid

from sqlalchemy import (
    TIMESTAMP,
    Boolean,
    Column,
    Float,
    ForeignKey,
    String,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB

from app.db.base import Base


def generate_prefixed_uuid() -> str:
    return f"wni_{uuid.uuid4()}"


class WorkflowNodeInstance(Base):
    __tablename__ = "workflow_node_instance"

    id = Column(String(), primary_key=True, default=generate_prefixed_uuid, nullable=False)
    workflow_id = Column(
        String(),
        ForeignKey("workflow.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    type_id = Column(String(), ForeignKey("workflow_node_type.id"), nullable=False, index=True)
    scene_id = Column(
        String(),
        ForeignKey("scene.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    x = Column(Float, nullable=False, default=0)
    y = Column(Float, nullable=False, default=0)
    w = Column(Float, nullable=True)
    h = Column(Float, nullable=True)
    label = Column(String(255), nullable=True)
    config = Column(JSONB, nullable=True)
    created_by = Column(String(), ForeignKey("user.id"), nullable=True)
    updated_by = Column(String(), ForeignKey("user.id"), nullable=True)
    is_deleted = Column(Boolean, nullable=False, default=False)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), nullable=False, default=func.now())
