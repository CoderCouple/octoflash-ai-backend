"""Job API — frontend polls this for render progress."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.tags import Tags
from app.api.v1.response.base_response import BaseResponse, success_response
from app.api.v1.response.job_response import JobResponse
from app.db.session import get_db
from app.service.job_service import JobService

router = APIRouter(tags=[Tags.Job])


def get_job_service(db: AsyncSession = Depends(get_db)) -> JobService:
    return JobService(db)


@router.get("/jobs/{job_id}", response_model=BaseResponse[JobResponse])
async def get_job(
    job_id: str,
    service: JobService = Depends(get_job_service),
):
    """Poll job status — { status, progress, logs, output_url? }."""
    result = await service.get_job(job_id)
    return success_response(result, "Job fetched")
