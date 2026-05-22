"""ExecutionPhase — one row per Temporal activity execution within a workflow run.

`node` is a snapshot of the workflow_node_instance id at run time (stored as
VARCHAR, NOT a FK) so deleting an instance later doesn't break lineage. The
temporal_* columns capture activity-level metadata: attempt count, heartbeat,
last failure.
"""

import uuid

from sqlalchemy import TIMESTAMP, Boolean, Column, ForeignKey, Integer, Numeric, String
from sqlalchemy import Enum as SAEnum
from sqlalchemy import func
from sqlalchemy.dialects.postgresql import JSONB

from app.common.enum.execution import ExecutionPhaseStatus
from app.db.base import Base


def generate_prefixed_uuid() -> str:
    return f"phase_{uuid.uuid4()}"


class ExecutionPhase(Base):
    __tablename__ = "execution_phase"

    id = Column(String(), primary_key=True, default=generate_prefixed_uuid, nullable=False)
    workflow_execution_id = Column(
        String(),
        ForeignKey("workflow_execution.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = Column(String(), ForeignKey("user.id"), nullable=False)
    status = Column(
        SAEnum(
            ExecutionPhaseStatus,
            name="execution_phase_status_enum",
            create_type=False,
            values_callable=lambda e: [v.value for v in e],
        ),
        nullable=False,
        default=ExecutionPhaseStatus.CREATED,
        index=True,
    )
    number = Column(Integer, nullable=False)
    node = Column(String(255), nullable=True)  # snapshot of workflow_node_instance.id
    name = Column(String(255), nullable=True)
    started_at = Column(TIMESTAMP(timezone=True), nullable=True)
    completed_at = Column(TIMESTAMP(timezone=True), nullable=True)
    inputs = Column(JSONB, nullable=True)
    outputs = Column(JSONB, nullable=True)
    credits_consumed = Column(Numeric, nullable=True)

    # Temporal-derived metadata.
    temporal_activity_id = Column(String(255), nullable=True)
    temporal_activity_type = Column(String(128), nullable=True)
    temporal_attempt = Column(Integer, nullable=True)
    temporal_max_attempts = Column(Integer, nullable=True)
    temporal_heartbeat_at = Column(TIMESTAMP(timezone=True), nullable=True)
    temporal_heartbeat_details = Column(JSONB, nullable=True)
    temporal_last_failure = Column(JSONB, nullable=True)

    created_by = Column(String(), ForeignKey("user.id"), nullable=True)
    updated_by = Column(String(), ForeignKey("user.id"), nullable=True)
    is_deleted = Column(Boolean, nullable=False, default=False)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), nullable=False, default=func.now())
