from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.response.plan_response import PlanFromPromptResponse
from app.api.v1.response.project_response import ProjectDetailResponse, ProjectResponse
from app.api.v1.response.scene_response import SceneResponse
from app.api.v1.response.workflow_response import (
    WorkflowEdgeResponse,
    WorkflowNodeResponse,
    WorkflowResponse,
)
from app.common.exceptions import EntityNotFoundError
from app.db.repository.project_repository import ProjectRepository
from app.db.repository.scene_repository import SceneRepository
from app.db.repository.workflow_repository import WorkflowRepository
from app.model.project_model import Project
from app.service.planner_service import PlannerService
from app.service.scene_service import SceneService


class ProjectService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.project_repo = ProjectRepository(db)
        self.scene_repo = SceneRepository(db)
        self.workflow_repo = WorkflowRepository(db)

    async def create_project(
        self,
        title: str,
        source_url: str | None = None,
        owner_id: str | None = None,
    ) -> ProjectResponse:
        project = Project(title=title, source_url=source_url, owner_id=owner_id)
        project = await self.project_repo.create(project)
        return ProjectResponse.model_validate(project)

    async def get_project_detail(self, project_id: str) -> ProjectDetailResponse:
        project = await self.project_repo.get_by_id(project_id)
        if not project:
            raise EntityNotFoundError("Project", project_id)

        scenes = await self.scene_repo.list_by_project(project_id)
        nodes = await self.workflow_repo.list_nodes(project_id)
        edges = await self.workflow_repo.list_edges(project_id)

        return ProjectDetailResponse(
            **ProjectResponse.model_validate(project).model_dump(),
            scenes=[SceneResponse.model_validate(s) for s in scenes],
            workflow=WorkflowResponse(
                nodes=[WorkflowNodeResponse.model_validate(n) for n in nodes],
                edges=[WorkflowEdgeResponse.model_validate(e) for e in edges],
            ),
        )

    async def list_projects(
        self, owner_id: str | None = None, offset: int = 0, limit: int = 20
    ) -> tuple[list[ProjectResponse], int]:
        projects, total = await self.project_repo.list_all(owner_id, offset, limit)
        return [ProjectResponse.model_validate(p) for p in projects], total

    async def update_project(
        self,
        project_id: str,
        title: str | None = None,
        source_url: str | None = None,
    ) -> ProjectResponse:
        project = await self.project_repo.get_by_id(project_id)
        if not project:
            raise EntityNotFoundError("Project", project_id)

        if title is not None:
            project.title = title
        if source_url is not None:
            project.source_url = source_url
        project.updated_at = datetime.now(timezone.utc)
        project = await self.project_repo.update(project)
        return ProjectResponse.model_validate(project)

    async def delete_project(self, project_id: str) -> None:
        project = await self.project_repo.get_by_id(project_id)
        if not project:
            raise EntityNotFoundError("Project", project_id)
        await self.project_repo.soft_delete(project)

    async def plan_scenes(
        self,
        project_id: str,
        prompt: str,
        style_preference: str | None = None,
        max_scenes: int | None = None,
        target_duration: float | None = None,
    ) -> PlanFromPromptResponse:
        """Plan a video from a prompt → create scenes in DB → return them.

        Sync: the Anthropic call is ~1-3s. We block, persist all scenes in
        one transaction, return them. No render is triggered — caller hits
        `POST /scenes/{id}/variations` per scene when ready.
        """
        project = await self.project_repo.get_by_id(project_id)
        if not project:
            raise EntityNotFoundError("Project", project_id)

        planner = PlannerService()
        planned, reasoning = await planner.plan_from_prompt(
            prompt=prompt,
            style_preference=style_preference,
            max_scenes=max_scenes,
            target_duration=target_duration,
        )

        scene_service = SceneService(self.db)
        created: list[SceneResponse] = []
        for spec in planned:
            scene = await scene_service.add_scene(
                project_id=project_id,
                template=spec.template,
                title=spec.title,
                prompt=spec.prompt,
                params=spec.params,
                duration=spec.duration,
                style=spec.style,
            )
            created.append(scene)

        return PlanFromPromptResponse(scenes=created, reasoning=reasoning)
