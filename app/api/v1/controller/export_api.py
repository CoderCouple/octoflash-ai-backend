"""Preview + export API — both return a Job to poll."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.tags import Tags
from app.api.v1.request.export_request import ExportRequest, PreviewRequest
from app.api.v1.response.base_response import BaseResponse, success_response
from app.api.v1.response.workflow_execution_response import WorkflowExecutionResponse
from app.common.auth.auth import UserContext, get_user_context_or_default
from app.db.session import get_db
from app.service.export_service import ExportService

router = APIRouter(tags=[Tags.Export])


def get_export_service(db: AsyncSession = Depends(get_db)) -> ExportService:
    return ExportService(db)


@router.post(
    "/projects/{project_id}/preview",
    response_model=BaseResponse[WorkflowExecutionResponse],
    status_code=202,
)
async def queue_preview(
    project_id: str,
    body: PreviewRequest,
    ctx: UserContext = Depends(get_user_context_or_default),
    service: ExportService = Depends(get_export_service),
):
    """Quick low-quality stitch along the selected path."""
    job = await service.queue_preview(
        project_id, user_id=ctx.user_id, end_node_id=body.end_node_id,
    )
    return success_response(job, "Preview queued", 202)


@router.post(
    "/projects/{project_id}/export",
    response_model=BaseResponse[WorkflowExecutionResponse],
    status_code=202,
)
async def queue_export(
    project_id: str,
    body: ExportRequest,
    ctx: UserContext = Depends(get_user_context_or_default),
    service: ExportService = Depends(get_export_service),
):
    """Full-quality stitch + encode."""
    job = await service.queue_export(
        project_id,
        user_id=ctx.user_id,
        end_node_id=body.end_node_id,
        format=body.format,
    )
    return success_response(job, "Export queued", 202)
