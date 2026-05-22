"""Repository for workflow_execution rows (replaces the old JobRepository).

A workflow_execution is one Temporal workflow run. Per-activity progress lives
in execution_phase rows; per-line logs in execution_log. This repository owns
all three tables' read/write paths so callers don't have to compose them.
"""

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.enum.execution import ExecutionStatus, LogLevel
from app.model.execution_log_model import ExecutionLog
from app.model.execution_phase_model import ExecutionPhase
from app.model.workflow_execution_model import WorkflowExecution


class WorkflowExecutionRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ── workflow_execution ──────────────────────────────────────────────

    async def get_by_id(self, execution_id: str) -> WorkflowExecution | None:
        result = await self.db.execute(
            select(WorkflowExecution).where(
                WorkflowExecution.id == execution_id,
                WorkflowExecution.is_deleted == False,  # noqa: E712
            )
        )
        return result.scalar_one_or_none()

    async def list_for_workflow(
        self, workflow_id: str, offset: int = 0, limit: int = 50
    ) -> tuple[list[WorkflowExecution], int]:
        base = select(WorkflowExecution).where(
            WorkflowExecution.workflow_id == workflow_id,
            WorkflowExecution.is_deleted == False,  # noqa: E712
        )
        count = await self.db.execute(select(func.count()).select_from(base.subquery()))
        total = count.scalar() or 0
        result = await self.db.execute(
            base.order_by(WorkflowExecution.created_at.desc()).offset(offset).limit(limit)
        )
        return list(result.scalars().all()), total

    async def create(self, execution: WorkflowExecution) -> WorkflowExecution:
        self.db.add(execution)
        await self.db.flush()
        return execution

    async def update(self, execution: WorkflowExecution) -> WorkflowExecution:
        execution.updated_at = datetime.now(timezone.utc)
        await self.db.flush()
        return execution

    # ── execution_phase ─────────────────────────────────────────────────

    async def list_phases(self, execution_id: str) -> list[ExecutionPhase]:
        result = await self.db.execute(
            select(ExecutionPhase)
            .where(
                ExecutionPhase.workflow_execution_id == execution_id,
                ExecutionPhase.is_deleted == False,  # noqa: E712
            )
            .order_by(ExecutionPhase.number.asc())
        )
        return list(result.scalars().all())

    async def create_phase(self, phase: ExecutionPhase) -> ExecutionPhase:
        self.db.add(phase)
        await self.db.flush()
        return phase

    async def update_phase(self, phase: ExecutionPhase) -> ExecutionPhase:
        phase.updated_at = datetime.now(timezone.utc)
        await self.db.flush()
        return phase

    # ── execution_log ───────────────────────────────────────────────────

    async def append_log(
        self,
        execution_phase_id: str,
        message: str,
        level: LogLevel = LogLevel.INFO,
        ts: datetime | None = None,
    ) -> ExecutionLog:
        log = ExecutionLog(
            execution_phase_id=execution_phase_id,
            log_level=level,
            message=message[:2048],  # column cap
            timestamp=ts or datetime.now(timezone.utc),
        )
        self.db.add(log)
        await self.db.flush()
        return log

    async def list_logs(self, execution_phase_id: str, limit: int = 200) -> list[ExecutionLog]:
        result = await self.db.execute(
            select(ExecutionLog)
            .where(
                ExecutionLog.execution_phase_id == execution_phase_id,
                ExecutionLog.is_deleted == False,  # noqa: E712
            )
            .order_by(ExecutionLog.timestamp.asc())
            .limit(limit)
        )
        return list(result.scalars().all())

    # ── convenience for the activity updater ────────────────────────────

    async def patch_status(
        self,
        execution_id: str,
        *,
        status: ExecutionStatus | None = None,
        temporal_workflow_id: str | None = None,
        temporal_run_id: str | None = None,
        started_at: datetime | None = None,
        completed_at: datetime | None = None,
        temporal_last_failure: dict[str, Any] | None = None,
    ) -> WorkflowExecution | None:
        execution = await self.get_by_id(execution_id)
        if execution is None:
            return None
        if status is not None:
            execution.status = status
            if status in (
                ExecutionStatus.COMPLETED,
                ExecutionStatus.FAILED,
                ExecutionStatus.CANCELED,
                ExecutionStatus.TERMINATED,
                ExecutionStatus.TIMED_OUT,
            ) and completed_at is None:
                completed_at = datetime.now(timezone.utc)
        if temporal_workflow_id is not None:
            execution.temporal_workflow_id = temporal_workflow_id
        if temporal_run_id is not None:
            execution.temporal_run_id = temporal_run_id
        if started_at is not None:
            execution.started_at = started_at
        if completed_at is not None:
            execution.completed_at = completed_at
        if temporal_last_failure is not None:
            execution.temporal_last_failure = temporal_last_failure
        await self.update(execution)
        return execution
