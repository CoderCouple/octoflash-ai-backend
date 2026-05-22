"""WorkflowEdgeInstance — per-canvas edge placement.

Projection of edges in `workflow.definition` JSONB. Same maintenance pattern
as workflow_node_instance: replaced on save. Source/target handle columns
mirror React Flow's `sourceHandle`/`targetHandle` for multi-port nodes.
"""

import uuid

from sqlalchemy import TIMESTAMP, Boolean, Column, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB

from app.db.base import Base


def generate_prefixed_uuid() -> str:
    return f"we_{uuid.uuid4()}"


class WorkflowEdgeInstance(Base):
    __tablename__ = "workflow_edge_instance"

    id = Column(String(), primary_key=True, default=generate_prefixed_uuid, nullable=False)
    workflow_id = Column(
        String(),
        ForeignKey("workflow.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_instance_id = Column(
        String(),
        ForeignKey("workflow_node_instance.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    target_instance_id = Column(
        String(),
        ForeignKey("workflow_node_instance.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_handle = Column(String(64), nullable=True)
    target_handle = Column(String(64), nullable=True)
    label = Column(String(255), nullable=True)
    data = Column(JSONB, nullable=True)
    created_by = Column(String(), ForeignKey("user.id"), nullable=True)
    updated_by = Column(String(), ForeignKey("user.id"), nullable=True)
    is_deleted = Column(Boolean, nullable=False, default=False)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), nullable=False, default=func.now())
