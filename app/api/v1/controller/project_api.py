"""Project API controller."""

from fastapi import APIRouter, Depends, Query
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.tags import Tags
from app.api.v1.request.from_source_request import CreateProjectFromSourceRequest
from app.api.v1.request.project_request import CreateProjectRequest, UpdateProjectRequest
from app.api.v1.response.base_response import BaseResponse, success_response
from app.api.v1.response.from_source_response import CreateProjectFromSourceResponse
from app.api.v1.response.workflow_execution_response import WorkflowExecutionResponse
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
    user_id: str | None = Query(default=None),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    service: ProjectService = Depends(get_project_service),
):
    """List projects."""
    projects, total = await service.list_projects(user_id, offset, limit)
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
    "/projects/from-source",
    response_model=BaseResponse[CreateProjectFromSourceResponse],
    status_code=202,
)
async def create_project_from_source(
    body: CreateProjectFromSourceRequest,
    service: ProjectService = Depends(get_project_service),
):
    """Create a project from a source URL and kick off analyze on Temporal.

    Returns 202 immediately with the empty Project + a Job to poll. The
    AnalyzeProjectWorkflow runs (download → frames → transcript → describer
    → prompt_builder), writes the brief onto the Project, and marks status
    `analyzed`. Frontend polls `GET /jobs/{job.id}` until done, then
    re-fetches `GET /projects/{id}` to see the editable brief.
    """
    result = await service.create_from_source(
        source_url=str(body.source_url),
        title=body.title,
        orientation=body.orientation,
        quality=body.quality,
        voiceover=body.voiceover,
        voice_id=body.voice_id,
        voice_gender=body.voice_gender,
        voice_accent=body.voice_accent,
        target_duration=body.target_duration,
    )
    return success_response(result, "Analyze workflow started", 202)


@router.post(
    "/projects/{project_id}/generate",
    response_model=BaseResponse[list[WorkflowExecutionResponse]],
    status_code=202,
)
async def generate_video(
    project_id: str,
    max_clips: int = Query(default=8, ge=1, le=20),
    orientations: list[str] = Query(
        default=["portrait", "landscape"],
        description="Which orientations to render. Default: both.",
    ),
    service: ProjectService = Depends(get_project_service),
):
    """Kick off one GenerateVideoWorkflow per requested orientation.

    Default produces BOTH `final_portrait_video_url` and
    `final_landscape_video_url` on the Project (each with its own scene set).
    Returns 202 with a list of executions — poll each at `/executions/:id`.
    """
    executions = await service.generate_video(
        project_id, max_clips=max_clips, orientations=orientations,
    )
    return success_response(executions, "Generate workflow(s) started", 202)


@router.get("/projects/{project_id}/preview")
async def preview_final_video(
    project_id: str,
    orientation: str = Query(
        default="portrait",
        description="Which orientation's final MP4 to stream.",
    ),
    service: ProjectService = Depends(get_project_service),
):
    """Stream the project's final stitched MP4 for the chosen orientation.
    404 if that orientation hasn't been generated yet."""
    path = await service.get_final_video_path(project_id, orientation=orientation)
    return FileResponse(
        path,
        media_type="video/mp4",
        filename=path.name,
        headers={"Cache-Control": "no-cache"},
    )
