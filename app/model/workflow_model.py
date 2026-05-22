"""Workflow — 1:1 child of project. The React Flow DAG source-of-truth.

`definition` JSONB holds the full React Flow tree (nodes + edges + viewport)
as serialised by `reactFlow.toObject()` on the client. Load = pass back to
React Flow verbatim. Save = replace JSON + sync workflow_node_instance +
workflow_edge_instance rows for queryability.

`execution_plan` JSONB is the derived topological order (cached so workers
don't have to recompute on every run).
"""

import uuid

from sqlalchemy import TIMESTAMP, Boolean, Column, ForeignKey, Numeric, String, func
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB

from app.common.enum.execution import WorkflowStatus
from app.db.base import Base


def generate_prefixed_uuid() -> str:
    return f"workflow_{uuid.uuid4()}"


class Workflow(Base):
    __tablename__ = "workflow"

    id = Column(String(), primary_key=True, default=generate_prefixed_uuid, nullable=False)
    project_id = Column(
        String(),
        ForeignKey("project.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    user_id = Column(String(), ForeignKey("user.id"), nullable=False, index=True)
    name = Column(String(255), nullable=True)
    description = Column(String(1024), nullable=True)
    definition = Column(JSONB, nullable=True)
    execution_plan = Column(JSONB, nullable=True)
    status = Column(
        SAEnum(
            WorkflowStatus,
            name="workflow_status_enum",
            create_type=False,
            values_callable=lambda e: [v.value for v in e],
        ),
        nullable=False,
        default=WorkflowStatus.DRAFT,
        index=True,
    )
    cron = Column(String(100), nullable=True)
    credits_cost = Column(Numeric, nullable=True)
    last_run_at = Column(TIMESTAMP(timezone=True), nullable=True)
    last_run_id = Column(String(64), nullable=True)
    last_run_status = Column(String(50), nullable=True)
    next_run_at = Column(TIMESTAMP(timezone=True), nullable=True)
    created_by = Column(String(), ForeignKey("user.id"), nullable=True)
    updated_by = Column(String(), ForeignKey("user.id"), nullable=True)
    is_deleted = Column(Boolean, nullable=False, default=False)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), nullable=False, default=func.now())
