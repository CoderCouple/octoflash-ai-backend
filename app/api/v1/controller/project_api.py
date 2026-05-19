"""Project API controller."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.tags import Tags
from app.api.v1.request.plan_request import PlanFromPromptRequest
from app.api.v1.request.project_request import CreateProjectRequest, UpdateProjectRequest
from app.api.v1.response.base_response import BaseResponse, success_response
from app.api.v1.response.plan_response import PlanFromPromptResponse
from app.api.v1.response.project_response import ProjectDetailResponse, ProjectResponse
from app.common.pagination import PaginatedResponse
from app.db.session import get_db
from app.service.project_service import ProjectService

router = APIRouter(tags=[Tags.Project])


def get_project_service(db: AsyncSession = Depends(get_db)) -> ProjectService:
    return ProjectService(db)


@router.post("/projects", response_model=BaseResponse[ProjectResponse], status_code=201)
async def create_project(
    body: CreateProjectRequest,
    service: ProjectService = Depends(get_project_service),
):
    """Create a new project."""
    result = await service.create_project(body.title, body.source_url)
    return success_response(result, "Project created", 201)


@router.get("/projects", response_model=BaseResponse[PaginatedResponse[ProjectResponse]])
async def list_projects(
    owner_id: str | None = Query(default=None),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    service: ProjectService = Depends(get_project_service),
):
    """List projects."""
    projects, total = await service.list_projects(owner_id, offset, limit)
    page = PaginatedResponse(items=projects, total=total, offset=offset, limit=limit)
    return success_response(page, "Projects fetched")


@router.get("/projects/{project_id}", response_model=BaseResponse[ProjectDetailResponse])
async def get_project(
    project_id: str,
    service: ProjectService = Depends(get_project_service),
):
    """Get project + scenes + workflow (matches frontend's project detail shape)."""
    result = await service.get_project_detail(project_id)
    return success_response(result, "Project fetched")


@router.patch("/projects/{project_id}", response_model=BaseResponse[ProjectResponse])
async def update_project(
    project_id: str,
    body: UpdateProjectRequest,
    service: ProjectService = Depends(get_project_service),
):
    """Rename project, update source_url, etc."""
    result = await service.update_project(project_id, title=body.title, source_url=body.source_url)
    return success_response(result, "Project updated")


@router.delete("/projects/{project_id}", response_model=BaseResponse)
async def delete_project(
    project_id: str,
    service: ProjectService = Depends(get_project_service),
):
    """Soft-delete a project."""
    await service.delete_project(project_id)
    return success_response(None, "Project deleted")


@router.post(
    "/projects/{project_id}/plan",
    response_model=BaseResponse[PlanFromPromptResponse],
    status_code=201,
)
async def plan_scenes_from_prompt(
    project_id: str,
    body: PlanFromPromptRequest,
    service: ProjectService = Depends(get_project_service),
):
    """Turn a freeform prompt into an ordered list of scenes, persisted in DB.

    Synchronous (Claude call is ~1–3s). Returns the created SceneResponses plus
    the planner's short reasoning. Does NOT trigger rendering — call
    `POST /scenes/{id}/variations` per scene when you're ready to render.
    """
    result = await service.plan_scenes(
        project_id=project_id,
        prompt=body.prompt,
        style_preference=body.style_preference,
        max_scenes=body.max_scenes,
        target_duration=body.target_duration,
    )
    return success_response(result, "Scenes planned", 201)
