"""WorkflowExecution — one row per Temporal workflow run.

Replaces the old `job` table. Carries Temporal handles (stable workflow_id +
rotating run_id) plus Temporal-derived metadata so the UI can show real
status, history size, last failure, retry counts, etc. without round-tripping
to the Temporal server on every poll.
"""

import uuid

from sqlalchemy import TIMESTAMP, BigInteger, Boolean, Column, ForeignKey, Integer, Numeric, String
from sqlalchemy import Enum as SAEnum
from sqlalchemy import func
from sqlalchemy.dialects.postgresql import JSONB

from app.common.enum.execution import ExecutionStatus, ExecutionTrigger, WorkflowKind
from app.db.base import Base


def generate_prefixed_uuid() -> str:
    return f"execution_{uuid.uuid4()}"


class WorkflowExecution(Base):
    __tablename__ = "workflow_execution"

    id = Column(String(), primary_key=True, default=generate_prefixed_uuid, nullable=False)
    workflow_id = Column(
        String(),
        ForeignKey("workflow.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # When the execution was kicked off via "Run" on a specific DAG node, this
    # points at that node. NULL for executions started by project-level routes
    # (POST /projects/from-source, POST /projects/{id}/generate) where the run
    # is for the whole project, not a single node. Indexed so the FE can show
    # per-node run history with a plain SQL WHERE.
    node_instance_id = Column(
        String(),
        ForeignKey("workflow_node_instance.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    user_id = Column(String(), ForeignKey("user.id"), nullable=False, index=True)
    kind = Column(
        SAEnum(
            WorkflowKind,
            name="workflow_kind_enum",
            create_type=False,
            values_callable=lambda e: [v.value for v in e],
        ),
        nullable=False,
    )
    trigger_kind = Column(
        SAEnum(
            ExecutionTrigger,
            name="execution_trigger_enum",
            create_type=False,
            values_callable=lambda e: [v.value for v in e],
        ),
        nullable=False,
        default=ExecutionTrigger.MANUAL,
    )
    status = Column(
        SAEnum(
            ExecutionStatus,
            name="execution_status_enum",
            create_type=False,
            values_callable=lambda e: [v.value for v in e],
        ),
        nullable=False,
        default=ExecutionStatus.PENDING,
        index=True,
    )
    credits_consumed = Column(Numeric, nullable=True)
    started_at = Column(TIMESTAMP(timezone=True), nullable=True)
    completed_at = Column(TIMESTAMP(timezone=True), nullable=True)

    # Temporal-derived metadata.
    temporal_workflow_id = Column(String(255), nullable=False, index=True)
    temporal_run_id = Column(String(64), nullable=True)
    temporal_workflow_type = Column(String(128), nullable=True)
    temporal_task_queue = Column(String(128), nullable=True)
    temporal_namespace = Column(String(128), nullable=True)
    temporal_parent_workflow_id = Column(String(255), nullable=True)
    temporal_parent_run_id = Column(String(64), nullable=True)
    temporal_history_length = Column(Integer, nullable=True)
    temporal_history_size_bytes = Column(BigInteger, nullable=True)
    temporal_last_failure = Column(JSONB, nullable=True)
    temporal_memo = Column(JSONB, nullable=True)
    temporal_search_attributes = Column(JSONB, nullable=True)

    created_by = Column(String(), ForeignKey("user.id"), nullable=True)
    updated_by = Column(String(), ForeignKey("user.id"), nullable=True)
    is_deleted = Column(Boolean, nullable=False, default=False)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), nullable=False, default=func.now())
