"""Workflow API — DAG nodes/edges, branches."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.tags import Tags
from app.api.v1.request.workflow_request import AddBranchRequest
from app.api.v1.response.base_response import BaseResponse, success_response
from app.api.v1.response.workflow_response import WorkflowResponse
from app.db.session import get_db
from app.service.workflow_service import WorkflowService

router = APIRouter(tags=[Tags.Workflow])


def get_workflow_service(db: AsyncSession = Depends(get_db)) -> WorkflowService:
    return WorkflowService(db)


@router.get(
    "/projects/{project_id}/workflow",
    response_model=BaseResponse[WorkflowResponse],
)
async def get_workflow(
    project_id: str,
    service: WorkflowService = Depends(get_workflow_service),
):
    """Return the DAG (nodes + edges) for the project."""
    result = await service.get_workflow(project_id)
    return success_response(result, "Workflow fetched")


@router.post(
    "/projects/{project_id}/workflow/branches",
    response_model=BaseResponse[WorkflowResponse],
    status_code=201,
)
async def add_branch(
    project_id: str,
    body: AddBranchRequest,
    service: WorkflowService = Depends(get_workflow_service),
):
    """Fan out into a new branch path (e.g. an alt 'manic' cut)."""
    result = await service.add_branch(
        project_id=project_id,
        from_node_id=body.from_node_id,
        branch_label=body.branch_label,
        style_override=body.style_override,
    )
    return success_response(result, "Branch added", 201)
