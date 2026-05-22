"""
DB write activities — execution-lineage updates.

Bridges Temporal workflows to the workflow_execution + execution_phase
tables. Status values on the input use canonical `ExecutionStatus` strings
(`PENDING` | `RUNNING` | `COMPLETED` | `FAILED` | `CANCELED` | `TERMINATED` |
`TIMED_OUT`); the activity constructs the enum directly. No legacy aliasing.

The legacy field name `log_entry` is preserved on the input — each entry
becomes a completed `execution_phase` row named after `log_entry["step"]`,
with the full dict in `outputs`. A richer "begin phase → heartbeat → complete
phase" surface can replace this when workflows are rewritten.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from temporalio import activity

# Side-effect import: ensures every model is in Base.metadata so FK resolution
# works inside activity-owned sessions (which don't share the request lifecycle).
import app.model  # noqa: F401
from app.common.enum.execution import ExecutionPhaseStatus, ExecutionStatus
from app.db.engine import get_async_engine
from app.db.repository.workflow_execution_repository import WorkflowExecutionRepository
from app.model.execution_phase_model import ExecutionPhase


def _session_factory() -> async_sessionmaker[AsyncSession]:
    """Build a fresh session factory bound to the worker's engine."""
    return async_sessionmaker(
        bind=get_async_engine(),
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )


@dataclass
class UpdateExecutionInput:
    execution_id: str
    status: str | None = None  # ExecutionStatus value, e.g. "RUNNING"
    log_entry: dict[str, Any] | None = None  # becomes an execution_phase row
    started_at: datetime | None = None
    completed_at: datetime | None = None
    temporal_workflow_id: str | None = None
    temporal_run_id: str | None = None


@activity.defn(name="update_execution")
async def update_execution_activity(payload: UpdateExecutionInput) -> None:
    """Patch the WorkflowExecution row and (if a log_entry is present) append
    a completed ExecutionPhase row for the step."""
    factory = _session_factory()
    async with factory() as session:
        repo = WorkflowExecutionRepository(session)
        execution = await repo.get_by_id(payload.execution_id)
        if execution is None:
            activity.logger.warning(
                "update_execution: execution %s not found", payload.execution_id
            )
            return

        new_status: ExecutionStatus | None = None
        if payload.status is not None:
            try:
                new_status = ExecutionStatus(payload.status)
            except ValueError:
                activity.logger.warning(
                    "update_execution: unknown status %r — leaving unchanged",
                    payload.status,
                )

        await repo.patch_status(
            execution.id,
            status=new_status,
            temporal_workflow_id=payload.temporal_workflow_id,
            temporal_run_id=payload.temporal_run_id,
            started_at=payload.started_at,
            completed_at=payload.completed_at,
        )

        if payload.log_entry is not None:
            existing = await repo.list_phases(execution.id)
            phase = ExecutionPhase(
                workflow_execution_id=execution.id,
                user_id=execution.user_id,
                status=ExecutionPhaseStatus.COMPLETED,
                number=len(existing) + 1,
                name=str(payload.log_entry.get("step") or f"step {len(existing) + 1}"),
                outputs=payload.log_entry,
                started_at=datetime.now(timezone.utc),
                completed_at=datetime.now(timezone.utc),
                temporal_activity_type=activity.info().activity_type,
                temporal_attempt=activity.info().attempt,
            )
            await repo.create_phase(phase)

        await session.commit()
