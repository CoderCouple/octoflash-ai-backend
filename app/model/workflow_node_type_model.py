"""WorkflowNodeType — global node-type library (NOT per-workflow).

Rows are reusable types like `source_url`, `scene`, `target`. The 4 seed rows
ship with the initial migration. Future custom types are inserted here once
and referenced by every workflow_node_instance.
"""

import uuid

from sqlalchemy import TIMESTAMP, Boolean, Column, ForeignKey, Integer, String, Text, func

from app.db.base import Base


def generate_prefixed_uuid() -> str:
    return f"node_{uuid.uuid4()}"


class WorkflowNodeType(Base):
    __tablename__ = "workflow_node_type"

    id = Column(String(), primary_key=True, default=generate_prefixed_uuid, nullable=False)
    name = Column(String(255), nullable=False)
    type = Column(String(100), unique=True, nullable=False)
    retries = Column(Integer, nullable=False, default=0)
    timeout_seconds = Column(Integer, nullable=False, default=30)
    error_message = Column(Text(), nullable=True)
    created_by = Column(String(), ForeignKey("user.id"), nullable=True)
    updated_by = Column(String(), ForeignKey("user.id"), nullable=True)
    is_deleted = Column(Boolean, nullable=False, default=False)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), nullable=False, default=func.now())
