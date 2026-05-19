from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.response.job_response import JobResponse
from app.api.v1.response.variation_response import VariationResponse
from app.common.enum.job import JobKind
from app.common.exceptions import EntityNotFoundError
from app.db.repository.scene_repository import SceneRepository
from app.db.repository.variation_repository import VariationRepository
from app.service.job_service import JobService
from app.settings import settings
from app.workers.client import get_temporal_client
from app.workers.workflows.variation_workflow import (
    GenerateVariationsInput,
    GenerateVariationsWorkflow,
    RerenderVariationInput,
    RerenderVariationWorkflow,
)


class VariationService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.variation_repo = VariationRepository(db)
        self.scene_repo = SceneRepository(db)
        self.job_service = JobService(db)

    async def generate_variations(
        self, scene_id: str, n: int = 4, seed: int | None = None
    ) -> JobResponse:
        scene = await self.scene_repo.get_by_id(scene_id)
        if not scene:
            raise EntityNotFoundError("Scene", scene_id)

        job = await self.job_service.create_job(JobKind.VARIATIONS, scene_id=scene_id)

        client = await get_temporal_client()
        workflow_id = f"{settings.temporal_workflow_id_prefix}-variations-{job.id}"
        handle = await client.start_workflow(
            GenerateVariationsWorkflow.run,
            GenerateVariationsInput(
                job_id=job.id,
                scene_id=scene_id,
                template_id=scene.template,
                params=dict(scene.params or {}),
                style=scene.style,
                extra_steps=list(scene.extra_steps or []),
                n=n,
                seed=seed,
            ),
            id=workflow_id,
            task_queue=settings.temporal_task_queue,
        )

        # Persist workflow handle so GET /jobs/{id} can correlate with Temporal.
        job_row = await self.job_service.job_repo.get_by_id(job.id)
        if job_row is not None:
            job_row.workflow_id = handle.id
            job_row.run_id = handle.first_execution_run_id
            await self.job_service.job_repo.update(job_row)

        return await self.job_service.get_job(job.id)

    async def list_for_scene(self, scene_id: str) -> list[VariationResponse]:
        variations = await self.variation_repo.list_by_scene(scene_id)
        return [VariationResponse.model_validate(v) for v in variations]

    async def rerender(
        self, variation_id: str, params_override: dict[str, Any] | None = None
    ) -> JobResponse:
        variation = await self.variation_repo.get_by_id(variation_id)
        if not variation:
            raise EntityNotFoundError("Variation", variation_id)
        scene = await self.scene_repo.get_by_id(variation.scene_id)
        if not scene:
            raise EntityNotFoundError("Scene", variation.scene_id)

        job = await self.job_service.create_job(
            JobKind.RERENDER, scene_id=variation.scene_id
        )

        client = await get_temporal_client()
        workflow_id = f"{settings.temporal_workflow_id_prefix}-rerender-{job.id}"
        handle = await client.start_workflow(
            RerenderVariationWorkflow.run,
            RerenderVariationInput(
                job_id=job.id,
                variation_id=variation.id,
                scene_id=scene.id,
                template_id=scene.template,
                params=params_override or dict(scene.params or {}),
                style=scene.style,
                extra_steps=list(scene.extra_steps or []),
                seed=None,
            ),
            id=workflow_id,
            task_queue=settings.temporal_task_queue,
        )

        job_row = await self.job_service.job_repo.get_by_id(job.id)
        if job_row is not None:
            job_row.workflow_id = handle.id
            job_row.run_id = handle.first_execution_run_id
            await self.job_service.job_repo.update(job_row)

        return await self.job_service.get_job(job.id)
