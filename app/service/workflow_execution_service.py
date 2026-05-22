"""WorkflowExecutionService — owns the workflow_execution + phase + log tables.

Every Temporal-workflow kickoff on the request path goes through here:

  1. `ensure_workflow_for_project()` lazily creates the Project's 1:1 Workflow row.
  2. `create_execution(kind=..., temporal_workflow_id=...)` inserts a row
     with status=PENDING.
  3. Caller starts the Temporal workflow.
  4. `stamp_handle(execution_id, temporal_run_id=...)` flips status → RUNNING.

The polling read is `get_response()` → WorkflowExecutionResponse with the
typed enum values and a derived `progress` int.
"""

from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.response.workflow_execution_response import (
    ExecutionPhaseResponse,
    WorkflowExecutionResponse,
)
from app.common.enum.execution import (
    ExecutionPhaseStatus,
    ExecutionStatus,
    ExecutionTrigger,
    LogLevel,
    WorkflowKind,
)
from app.common.exceptions import EntityNotFoundError
from app.db.repository.project_repository import ProjectRepository
from app.db.repository.workflow_execution_repository import WorkflowExecutionRepository
from app.db.repository.workflow_repository import WorkflowRepository
from app.model.workflow_execution_model import WorkflowExecution
from app.model.workflow_model import Workflow
from app.settings import settings


class WorkflowExecutionService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.execution_repo = WorkflowExecutionRepository(db)
        self.workflow_repo = WorkflowRepository(db)
        self.project_repo = ProjectRepository(db)

    async def ensure_workflow_for_project(self, project_id: str) -> Workflow:
        """Return the Project's 1:1 Workflow row, lazily creating an empty one."""
        existing = await self.workflow_repo.get_by_project_id(project_id)
        if existing is not None:
            return existing
        project = await self.project_repo.get_by_id(project_id)
        if project is None:
            raise EntityNotFoundError("Project", project_id)
        workflow = Workflow(
            project_id=project_id,
            user_id=project.user_id,
            name=project.title,
        )
        return await self.workflow_repo.create(workflow)

    async def create_execution(
        self,
        *,
        project_id: str,
        kind: WorkflowKind,
        temporal_workflow_id: str,
        temporal_workflow_type: str,
        trigger: ExecutionTrigger = ExecutionTrigger.MANUAL,
        user_id: str | None = None,
    ) -> WorkflowExecution:
        """Insert a WorkflowExecution row stamped with the temporal id we'll use.

        Call this BEFORE `client.start_workflow(...)`. After start, call
        `stamp_handle()` to flip status → RUNNING + record the run_id.
        """
        workflow = await self.ensure_workflow_for_project(project_id)
        execution = WorkflowExecution(
            workflow_id=workflow.id,
            user_id=user_id or workflow.user_id or settings.default_user_id,
            kind=kind,
            trigger_kind=trigger,
            status=ExecutionStatus.PENDING,
            temporal_workflow_id=temporal_workflow_id,
            temporal_workflow_type=temporal_workflow_type,
            temporal_task_queue=settings.temporal_task_queue,
            temporal_namespace=settings.temporal_namespace,
        )
        return await self.execution_repo.create(execution)

    async def stamp_handle(
        self,
        execution_id: str,
        *,
        temporal_run_id: str,
        started_at: datetime | None = None,
    ) -> WorkflowExecution | None:
        """Once Temporal returns the handle, record run_id + flip to RUNNING."""
        return await self.execution_repo.patch_status(
            execution_id,
            status=ExecutionStatus.RUNNING,
            temporal_run_id=temporal_run_id,
            started_at=started_at or datetime.now(timezone.utc),
        )

    async def get(self, execution_id: str) -> WorkflowExecution:
        execution = await self.execution_repo.get_by_id(execution_id)
        if execution is None:
            raise EntityNotFoundError("WorkflowExecution", execution_id)
        return execution

    async def get_response(self, execution_id: str) -> WorkflowExecutionResponse:
        execution = await self.get(execution_id)
        phases = await self.execution_repo.list_phases(execution_id)

        if phases:
            completed = sum(1 for p in phases if p.status == ExecutionPhaseStatus.COMPLETED)
            progress = int((completed / len(phases)) * 100)
        else:
            # Pre-phase fallback so the FE has something to show.
            progress = {
                ExecutionStatus.PENDING: 0,
                ExecutionStatus.RUNNING: 10,
                ExecutionStatus.COMPLETED: 100,
                ExecutionStatus.FAILED: 100,
                ExecutionStatus.CANCELED: 100,
                ExecutionStatus.TERMINATED: 100,
                ExecutionStatus.TIMED_OUT: 100,
            }.get(execution.status, 0)

        return WorkflowExecutionResponse(
            id=execution.id,
            workflow_id=execution.workflow_id,
            user_id=execution.user_id,
            kind=execution.kind,
            trigger_kind=execution.trigger_kind,
            status=execution.status,
            progress=progress,
            started_at=execution.started_at,
            completed_at=execution.completed_at,
            credits_consumed=(
                float(execution.credits_consumed) if execution.credits_consumed is not None else None
            ),
            temporal_workflow_id=execution.temporal_workflow_id,
            temporal_run_id=execution.temporal_run_id,
            temporal_workflow_type=execution.temporal_workflow_type,
            temporal_task_queue=execution.temporal_task_queue,
            temporal_namespace=execution.temporal_namespace,
            temporal_history_length=execution.temporal_history_length,
            temporal_history_size_bytes=execution.temporal_history_size_bytes,
            temporal_last_failure=execution.temporal_last_failure,
            phases=[ExecutionPhaseResponse.model_validate(p) for p in phases],
            created_at=execution.created_at,
            updated_at=execution.updated_at,
        )

    async def append_phase_log(
        self,
        phase_id: str,
        message: str,
        level: LogLevel = LogLevel.INFO,
    ) -> None:
        await self.execution_repo.append_log(phase_id, message, level)
