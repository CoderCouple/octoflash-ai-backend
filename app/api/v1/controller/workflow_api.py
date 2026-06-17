"""Workflow API — the DAG load/save surface.

  GET  /projects/{project_id}/workflow  → sugar: get-or-create
  GET  /workflows/{workflow_id}         → load
  PUT  /workflows/{workflow_id}         → replace (React Flow toObject payload)
"""

from typing import Any

from fastapi import APIRouter, Body, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.tags import Tags
from app.api.v1.request.workflow_request import PutWorkflowRequest
from app.api.v1.response.base_response import BaseResponse, success_response
from app.api.v1.response.workflow_execution_response import WorkflowExecutionResponse
from app.api.v1.response.workflow_response import WorkflowResponse
from app.common.auth.auth import UserContext, get_user_context_or_default
from app.common.exceptions import EntityNotFoundError
from app.db.repository.workflow_repository import WorkflowRepository
from app.db.session import get_db
from app.service.node_runner_service import NodeRunnerService
from app.service.project_service import ProjectService
from app.service.workflow_service import WorkflowService

router = APIRouter(tags=[Tags.Workflow])


def get_workflow_service(db: AsyncSession = Depends(get_db)) -> WorkflowService:
    return WorkflowService(db)


def get_node_runner_service(db: AsyncSession = Depends(get_db)) -> NodeRunnerService:
    return NodeRunnerService(db)


class RunNodeRequest(BaseModel):
    """One-shot per-run overrides; empty body uses node.config from the saved DAG."""

    inputs: dict[str, Any] = Field(default_factory=dict)


@router.get(
    "/projects/{project_id}/workflow",
    response_model=BaseResponse[WorkflowResponse],
)
async def get_workflow_for_project(
    project_id: str,
    ctx: UserContext = Depends(get_user_context_or_default),
    service: WorkflowService = Depends(get_workflow_service),
):
    """Return the Project's 1:1 workflow. Lazily creates an empty one if missing."""
    # service-side tenant filter is a follow-up.
    result = await service.get_for_project(project_id)
    return success_response(result, "Workflow fetched")


@router.get(
    "/workflows/{workflow_id}",
    response_model=BaseResponse[WorkflowResponse],
)
async def get_workflow(
    workflow_id: str,
    ctx: UserContext = Depends(get_user_context_or_default),
    service: WorkflowService = Depends(get_workflow_service),
):
    """Get a workflow by id. `definition` is the React Flow source-of-truth."""
    # service-side tenant filter is a follow-up.
    result = await service.get_by_id(workflow_id)
    return success_response(result, "Workflow fetched")


@router.put(
    "/workflows/{workflow_id}",
    response_model=BaseResponse[WorkflowResponse],
)
async def put_workflow(
    workflow_id: str,
    body: PutWorkflowRequest,
    ctx: UserContext = Depends(get_user_context_or_default),
    service: WorkflowService = Depends(get_workflow_service),
):
    """Replace the workflow's canvas state (React Flow's `toObject()` payload).

    Persists `definition` JSONB verbatim AND syncs the projection rows in
    workflow_node_instance + workflow_edge_instance for queryability.
    """
    # service-side tenant filter is a follow-up.
    result = await service.put_definition(workflow_id, body)
    return success_response(result, "Workflow saved")


@router.delete(
    "/workflows/{workflow_id}",
    response_model=BaseResponse,
)
async def delete_workflow(
    workflow_id: str,
    ctx: UserContext = Depends(get_user_context_or_default),
    db: AsyncSession = Depends(get_db),
):
    """Delete the workflow AND its parent project (they're 1:1).

    Cascades through the full cleanup chain in ProjectService.delete_project:
    in-flight Temporal workflows terminated, executions canceled, project +
    workflow soft-deleted, local storage rmtree'd.
    """
    # service-side tenant filter is a follow-up.
    workflow = await WorkflowRepository(db).get_by_id(workflow_id)
    if workflow is None:
        raise EntityNotFoundError("Workflow", workflow_id)
    await ProjectService(db).delete_project(workflow.project_id)
    return success_response(None, "Workflow + project deleted")


@router.delete(
    "/workflows/{workflow_id}/nodes/{node_instance_id}",
    response_model=BaseResponse,
)
async def delete_workflow_node(
    workflow_id: str,
    node_instance_id: str,
    ctx: UserContext = Depends(get_user_context_or_default),
    service: WorkflowService = Depends(get_workflow_service),
):
    """Delete one DAG node + its edges, terminate any in-flight runs for it.

    Cancels (Temporal terminate + DB CANCELED) every workflow_execution
    whose node_instance_id matches. Strips the node + touching edges from
    workflow.definition; hard-deletes the projection row (FK CASCADE drops
    touching edge rows). Historical execution rows survive via
    `workflow_execution.node_instance_id ON DELETE SET NULL`.
    """
    # service-side tenant filter is a follow-up.
    await service.delete_node(workflow_id, node_instance_id)
    return success_response(None, "Node deleted")


@router.post(
    "/workflows/{workflow_id}/nodes/{node_instance_id}/run",
    response_model=BaseResponse[WorkflowExecutionResponse],
    status_code=202,
)
async def run_node(
    workflow_id: str,
    node_instance_id: str,
    body: RunNodeRequest = Body(default_factory=RunNodeRequest),
    ctx: UserContext = Depends(get_user_context_or_default),
    runner: NodeRunnerService = Depends(get_node_runner_service),
):
    """Trigger a Temporal workflow for one DAG node ("Run" / "Regenerate" button).

    Coalesced via deterministic temporal_workflow_id: clicking twice with the
    same `inputs` returns the in-flight execution. Different inputs → new run.
    `WorkflowExecutionResponse` is returned; FE polls `GET /executions/:id`.
    """
    # service-side tenant filter is a follow-up.
    result = await runner.run_node(
        workflow_id=workflow_id,
        node_instance_id=node_instance_id,
        inputs_override=body.inputs or None,
    )
    return success_response(result, "Node run started", 202)
