"""Project API controller."""

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.service.supabase_storage_service import get_storage_service

from app.api.tags import Tags
from app.api.v1.request.from_source_request import CreateProjectFromSourceRequest
from app.api.v1.request.project_request import CreateProjectRequest, UpdateProjectRequest
from app.api.v1.response.base_response import BaseResponse, success_response
from app.api.v1.response.from_source_response import CreateProjectFromSourceResponse
from app.api.v1.response.workflow_execution_response import WorkflowExecutionResponse
from app.api.v1.response.project_response import ProjectDetailResponse, ProjectResponse
from app.common.auth.auth import UserContext, get_user_context_or_default
from app.common.pagination import PaginatedResponse
from app.db.session import get_db
from app.service.project_service import ProjectService

router = APIRouter(tags=[Tags.Project])


def get_project_service(db: AsyncSession = Depends(get_db)) -> ProjectService:
    return ProjectService(db)


@router.post("/projects", response_model=BaseResponse[ProjectResponse], status_code=201)
async def create_project(
    body: CreateProjectRequest,
    ctx: UserContext = Depends(get_user_context_or_default),
    service: ProjectService = Depends(get_project_service),
):
    """Create a new project."""
    result = await service.create_project(
        body.title,
        body.source_url,
        user_id=ctx.user_id,
        org_id=ctx.organization_id,
        workspace_id=ctx.workspace_id,
    )
    return success_response(result, "Project created", 201)


@router.get("/projects", response_model=BaseResponse[PaginatedResponse[ProjectResponse]])
async def list_projects(
    ctx: UserContext = Depends(get_user_context_or_default),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    service: ProjectService = Depends(get_project_service),
):
    """List projects."""
    projects, total = await service.list_projects(
        ctx.user_id,
        offset,
        limit,
        org_id=ctx.organization_id,
        workspace_id=ctx.workspace_id,
    )
    page = PaginatedResponse(items=projects, total=total, offset=offset, limit=limit)
    return success_response(page, "Projects fetched")


@router.get("/projects/{project_id}", response_model=BaseResponse[ProjectDetailResponse])
async def get_project(
    project_id: str,
    ctx: UserContext = Depends(get_user_context_or_default),
    service: ProjectService = Depends(get_project_service),
):
    """Get project + scenes + workflow (matches frontend's project detail shape)."""
    # service-side tenant filter is a follow-up.
    result = await service.get_project_detail(project_id)
    return success_response(result, "Project fetched")


@router.patch("/projects/{project_id}", response_model=BaseResponse[ProjectResponse])
async def update_project(
    project_id: str,
    body: UpdateProjectRequest,
    ctx: UserContext = Depends(get_user_context_or_default),
    service: ProjectService = Depends(get_project_service),
):
    """Rename project, update source_url, etc."""
    # service-side tenant filter is a follow-up.
    result = await service.update_project(project_id, title=body.title, source_url=body.source_url)
    return success_response(result, "Project updated")


@router.delete("/projects/{project_id}", response_model=BaseResponse)
async def delete_project(
    project_id: str,
    ctx: UserContext = Depends(get_user_context_or_default),
    service: ProjectService = Depends(get_project_service),
):
    """Soft-delete a project."""
    # service-side tenant filter is a follow-up.
    await service.delete_project(project_id)
    return success_response(None, "Project deleted")


@router.post(
    "/projects/from-source",
    response_model=BaseResponse[CreateProjectFromSourceResponse],
    status_code=202,
)
async def create_project_from_source(
    body: CreateProjectFromSourceRequest,
    ctx: UserContext = Depends(get_user_context_or_default),
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
        user_id=ctx.user_id,
        org_id=ctx.organization_id,
        workspace_id=ctx.workspace_id,
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
    ctx: UserContext = Depends(get_user_context_or_default),
    service: ProjectService = Depends(get_project_service),
):
    """Kick off one GenerateVideoWorkflow per requested orientation.

    Default produces BOTH `final_portrait_video_url` and
    `final_landscape_video_url` on the Project (each with its own scene set).
    Returns 202 with a list of executions — poll each at `/executions/:id`.
    """
    # service-side tenant filter is a follow-up.
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
    ctx: UserContext = Depends(get_user_context_or_default),
    service: ProjectService = Depends(get_project_service),
):
    """Hand the FE a playable URL for the project's final MP4.

    For renders that landed in Supabase Storage (the prod path — every
    new generation since the storage migration) we mint a fresh signed
    URL on demand and 302 the client to it. For legacy local-disk
    records (older dev runs only) we still stream the file directly so
    nothing already in the dev DB breaks.
    """
    # service-side tenant filter is a follow-up.
    ref = await service.get_final_video_ref(project_id, orientation=orientation)

    if ref.startswith("supabase://"):
        # Format: supabase://<bucket>/<path>. Re-sign every call so the
        # URL is fresh; signed URLs expire after 1h so we don't ever
        # persist them.
        rest = ref[len("supabase://"):]
        bucket, _, object_path = rest.partition("/")
        if not bucket or not object_path:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Malformed storage reference: {ref}",
            )
        signed = get_storage_service().signed_url(bucket, object_path)
        return RedirectResponse(signed, status_code=status.HTTP_302_FOUND)

    # Legacy: local path on disk (older dev renders pre-Supabase swap).
    path = Path(ref)
    if not path.exists():
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail=f"final video reference points at missing file: {path}",
        )
    return FileResponse(
        path,
        media_type="video/mp4",
        filename=path.name,
        headers={"Cache-Control": "no-cache"},
    )
