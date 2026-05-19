from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.response.job_response import JobResponse
from app.common.enum.job import JobKind
from app.service.job_service import JobService
from app.settings import settings
from app.workers.client import get_temporal_client
from app.workers.workflows.export_workflow import (
    ExportProjectInput,
    ExportProjectWorkflow,
    PreviewProjectInput,
    PreviewProjectWorkflow,
)


class ExportService:
    """Orchestrates preview/export stitching via Temporal workflows.

    Both return 202 + Job immediately; the workflows fan out the per-scene
    work and update the Job row as they progress. Frontend polls `/jobs/{id}`.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.job_service = JobService(db)

    async def queue_preview(
        self, project_id: str, end_node_id: str | None = None
    ) -> JobResponse:
        job = await self.job_service.create_job(JobKind.PREVIEW, project_id=project_id)

        client = await get_temporal_client()
        workflow_id = f"{settings.temporal_workflow_id_prefix}-preview-{job.id}"
        handle = await client.start_workflow(
            PreviewProjectWorkflow.run,
            PreviewProjectInput(job_id=job.id, project_id=project_id),
            id=workflow_id,
            task_queue=settings.temporal_task_queue,
        )
        job_row = await self.job_service.job_repo.get_by_id(job.id)
        if job_row is not None:
            job_row.workflow_id = handle.id
            job_row.run_id = handle.first_execution_run_id
            await self.job_service.job_repo.update(job_row)
        return await self.job_service.get_job(job.id)

    async def queue_export(
        self, project_id: str, end_node_id: str | None = None, format: str = "mp4"
    ) -> JobResponse:
        job = await self.job_service.create_job(JobKind.EXPORT, project_id=project_id)

        client = await get_temporal_client()
        workflow_id = f"{settings.temporal_workflow_id_prefix}-export-{job.id}"
        handle = await client.start_workflow(
            ExportProjectWorkflow.run,
            ExportProjectInput(job_id=job.id, project_id=project_id, format=format),
            id=workflow_id,
            task_queue=settings.temporal_task_queue,
        )
        job_row = await self.job_service.job_repo.get_by_id(job.id)
        if job_row is not None:
            job_row.workflow_id = handle.id
            job_row.run_id = handle.first_execution_run_id
            await self.job_service.job_repo.update(job_row)
        return await self.job_service.get_job(job.id)
