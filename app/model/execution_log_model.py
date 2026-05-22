"""ExecutionLog — log line under an execution_phase. Append-only."""

import uuid

from sqlalchemy import TIMESTAMP, Boolean, Column, ForeignKey, String, func
from sqlalchemy import Enum as SAEnum

from app.common.enum.execution import LogLevel
from app.db.base import Base


def generate_prefixed_uuid() -> str:
    return f"execlog_{uuid.uuid4()}"


class ExecutionLog(Base):
    __tablename__ = "execution_log"

    id = Column(String(), primary_key=True, default=generate_prefixed_uuid, nullable=False)
    execution_phase_id = Column(
        String(),
        ForeignKey("execution_phase.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    log_level = Column(
        SAEnum(
            LogLevel,
            name="log_level_enum",
            create_type=False,
            values_callable=lambda e: [v.value for v in e],
        ),
        nullable=False,
    )
    message = Column(String(2048), nullable=False)
    timestamp = Column(TIMESTAMP(timezone=True), nullable=False)
    created_by = Column(String(), ForeignKey("user.id"), nullable=True)
    updated_by = Column(String(), ForeignKey("user.id"), nullable=True)
    is_deleted = Column(Boolean, nullable=False, default=False)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), nullable=False, default=func.now())
