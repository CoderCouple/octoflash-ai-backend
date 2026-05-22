"""Preview + export API — both return a Job to poll."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.tags import Tags
from app.api.v1.request.export_request import ExportRequest, PreviewRequest
from app.api.v1.response.base_response import BaseResponse, success_response
from app.api.v1.response.workflow_execution_response import WorkflowExecutionResponse
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
    service: ExportService = Depends(get_export_service),
):
    """Quick low-quality stitch along the selected path."""
    job = await service.queue_preview(project_id, end_node_id=body.end_node_id)
    return success_response(job, "Preview queued", 202)


@router.post(
    "/projects/{project_id}/export",
    response_model=BaseResponse[WorkflowExecutionResponse],
    status_code=202,
)
async def queue_export(
    project_id: str,
    body: ExportRequest,
    service: ExportService = Depends(get_export_service),
):
    """Full-quality stitch + encode."""
    job = await service.queue_export(project_id, end_node_id=body.end_node_id, format=body.format)
    return success_response(job, "Export queued", 202)
