from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.response.job_response import JobResponse
from app.common.enum.job import JobKind, JobStatus
from app.common.exceptions import EntityNotFoundError
from app.db.repository.job_repository import JobRepository
from app.model.job_model import Job


class JobService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.job_repo = JobRepository(db)

    async def create_job(
        self,
        kind: JobKind,
        project_id: str | None = None,
        scene_id: str | None = None,
    ) -> JobResponse:
        job = Job(
            kind=kind.value,
            project_id=project_id,
            scene_id=scene_id,
            status=JobStatus.QUEUED.value,
            progress=0,
        )
        job = await self.job_repo.create(job)
        return JobResponse.model_validate(job)

    async def get_job(self, job_id: str) -> JobResponse:
        job = await self.job_repo.get_by_id(job_id)
        if not job:
            raise EntityNotFoundError("Job", job_id)
        return JobResponse.model_validate(job)
