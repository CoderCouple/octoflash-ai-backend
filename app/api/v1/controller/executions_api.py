"""Polling controller for workflow_execution rows.

  GET /executions/{id} → WorkflowExecutionResponse

This replaces the legacy /jobs/{id} polling URL. The response carries the
real ExecutionStatus + WorkflowKind enum values (no legacy aliasing),
a derived progress int, and the list of execution_phase rows.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.tags import Tags
from app.api.v1.response.base_response import BaseResponse, success_response
from app.api.v1.response.workflow_execution_response import WorkflowExecutionResponse
from app.common.auth.auth import UserContext, get_user_context_or_default
from app.db.session import get_db
from app.service.workflow_execution_service import WorkflowExecutionService

router = APIRouter(tags=[Tags.Job])


def get_execution_service(db: AsyncSession = Depends(get_db)) -> WorkflowExecutionService:
    return WorkflowExecutionService(db)


@router.get(
    "/executions/{execution_id}",
    response_model=BaseResponse[WorkflowExecutionResponse],
)
async def get_execution(
    execution_id: str,
    ctx: UserContext = Depends(get_user_context_or_default),
    service: WorkflowExecutionService = Depends(get_execution_service),
):
    """Poll a workflow_execution by id."""
    response = await service.get_response(execution_id, user_id=ctx.user_id)
    return success_response(response, "Execution fetched")
