import uuid

from sqlalchemy import TIMESTAMP, Column, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB

from app.db.base import Base


def generate_prefixed_uuid() -> str:
    return f"job_{uuid.uuid4()}"


class Job(Base):
    __tablename__ = "job"

    id = Column(String(), primary_key=True, default=generate_prefixed_uuid, nullable=False)
    kind = Column(String(32), nullable=False)  # JobKind
    project_id = Column(String(), nullable=True, index=True)
    scene_id = Column(String(), nullable=True, index=True)
    status = Column(String(16), nullable=False, default="queued")  # JobStatus
    progress = Column(Integer, nullable=False, default=0)
    logs = Column(JSONB, nullable=False, default=list)
    output_url = Column(Text(), nullable=True)

    # Temporal handles — set when the Job is backed by a workflow execution.
    # `run_id` rotates if a workflow is restarted; `workflow_id` is stable.
    workflow_id = Column(String(), nullable=True, index=True)
    run_id = Column(String(), nullable=True)

    started_at = Column(TIMESTAMP(timezone=True), nullable=True)
    finished_at = Column(TIMESTAMP(timezone=True), nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), default=func.now(), nullable=False)
