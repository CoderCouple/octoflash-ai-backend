from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.model.job_model import Job


class JobRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, job_id: str) -> Job | None:
        result = await self.db.execute(select(Job).where(Job.id == job_id))
        return result.scalar_one_or_none()

    async def create(self, job: Job) -> Job:
        self.db.add(job)
        await self.db.flush()
        return job

    async def update(self, job: Job) -> Job:
        await self.db.flush()
        return job
