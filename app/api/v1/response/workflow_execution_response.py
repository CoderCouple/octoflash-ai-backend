"""Response models for the /executions surface — proper typed replacement
for the legacy job_response. ExecutionStatus / WorkflowKind values are
returned verbatim (no string aliasing); per-phase + per-log detail can be
expanded as the FE consumes more of the shape.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict

from app.common.enum.execution import (
    ExecutionPhaseStatus,
    ExecutionStatus,
    ExecutionTrigger,
    LogLevel,
    WorkflowKind,
)


class ExecutionPhaseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    workflow_execution_id: str
    status: ExecutionPhaseStatus
    number: int
    name: str | None = None
    node: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    inputs: dict[str, Any] | None = None
    outputs: dict[str, Any] | None = None
    temporal_activity_id: str | None = None
    temporal_activity_type: str | None = None
    temporal_attempt: int | None = None
    temporal_max_attempts: int | None = None
    temporal_heartbeat_at: datetime | None = None
    temporal_last_failure: dict[str, Any] | None = None
    created_at: datetime
    updated_at: datetime


class ExecutionLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    execution_phase_id: str
    log_level: LogLevel
    message: str
    timestamp: datetime


class WorkflowExecutionResponse(BaseModel):
    """One workflow_execution row plus its phases — what the FE polls."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    workflow_id: str
    # Surface the parent project so callers can navigate to /projects/{id}
    # after kicking a workflow. Nullable for executions tied to a workflow
    # whose project linkage isn't set (rare; safe default).
    project_id: str | None = None
    user_id: str
    kind: WorkflowKind
    trigger_kind: ExecutionTrigger
    status: ExecutionStatus

    # Derived progress: ratio of COMPLETED phases over total phases.
    # 0-100. The service fills this in (not from a column).
    progress: int = 0

    started_at: datetime | None = None
    completed_at: datetime | None = None
    credits_consumed: float | None = None

    # Temporal lineage
    temporal_workflow_id: str
    temporal_run_id: str | None = None
    temporal_workflow_type: str | None = None
    temporal_task_queue: str | None = None
    temporal_namespace: str | None = None
    temporal_history_length: int | None = None
    temporal_history_size_bytes: int | None = None
    temporal_last_failure: dict[str, Any] | None = None

    phases: list[ExecutionPhaseResponse] = []

    created_at: datetime
    updated_at: datetime
