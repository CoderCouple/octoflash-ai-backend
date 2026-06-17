"""Scene API controller — scene CRUD + per-clip preview + per-clip regenerate.

A Scene in the current model is a clip in a Project's plan. Editor UX:
  - PATCH /scenes/{id}           → edit prompt, title, duration (sync, no render)
  - GET   /scenes/{id}           → fetch one scene for FE polling
  - GET   /scenes/{id}/preview   → stream the clip's MP4 in the browser
  - POST  /scenes/{id}/regenerate → kicks off RegenerateClipWorkflow (per-clip
                                    re-render + auto-restitch the project)
"""

from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.tags import Tags
from app.api.v1.request.scene_request import CreateSceneRequest, UpdateSceneRequest
from app.api.v1.response.base_response import BaseResponse, success_response
from app.api.v1.response.workflow_execution_response import WorkflowExecutionResponse
from app.api.v1.response.scene_response import SceneResponse
from app.common.auth.auth import UserContext, get_user_context_or_default
from app.db.session import get_db
from app.service.scene_service import SceneService

router = APIRouter(tags=[Tags.Scene])


def get_scene_service(db: AsyncSession = Depends(get_db)) -> SceneService:
    return SceneService(db)


@router.get("/scenes/{scene_id}", response_model=BaseResponse[SceneResponse])
async def get_scene(
    scene_id: str,
    ctx: UserContext = Depends(get_user_context_or_default),
    service: SceneService = Depends(get_scene_service),
):
    """Fetch one scene — used by FE for per-clip status polling during render."""
    result = await service.get_scene(scene_id, user_id=ctx.user_id)
    return success_response(result, "Scene fetched")


@router.get("/scenes/{scene_id}/preview")
async def preview_scene(
    scene_id: str,
    ctx: UserContext = Depends(get_user_context_or_default),
    service: SceneService = Depends(get_scene_service),
):
    """Stream the clip's MP4 — what the FE's per-node `<video>` element loads."""
    path = await service.get_scene_preview_path(scene_id, user_id=ctx.user_id)
    return FileResponse(
        path,
        media_type="video/mp4",
        filename=path.name,
        headers={"Cache-Control": "no-cache"},
    )


@router.post(
    "/scenes/{scene_id}/regenerate",
    response_model=BaseResponse[WorkflowExecutionResponse],
    status_code=202,
)
async def regenerate_clip(
    scene_id: str,
    ctx: UserContext = Depends(get_user_context_or_default),
    service: SceneService = Depends(get_scene_service),
):
    """Kick off RegenerateClipWorkflow — re-render this clip + auto-restitch project.

    Returns 202 + a Job to poll. Editing the clip's prompt first via PATCH
    /scenes/{id} is the typical flow before calling this.
    """
    job = await service.regenerate_clip(scene_id, user_id=ctx.user_id)
    return success_response(job, "Regenerate workflow started", 202)


@router.post(
    "/projects/{project_id}/scenes",
    response_model=BaseResponse[SceneResponse],
    status_code=201,
)
async def add_scene(
    project_id: str,
    body: CreateSceneRequest,
    ctx: UserContext = Depends(get_user_context_or_default),
    service: SceneService = Depends(get_scene_service),
):
    """Add a scene to a project."""
    result = await service.add_scene(
        project_id=project_id,
        user_id=ctx.user_id,
        title=body.title,
        prompt=body.prompt,
        duration=body.duration,
        n=body.n,
    )
    return success_response(result, "Scene added", 201)


@router.patch("/scenes/{scene_id}", response_model=BaseResponse[SceneResponse])
async def update_scene(
    scene_id: str,
    body: UpdateSceneRequest,
    ctx: UserContext = Depends(get_user_context_or_default),
    service: SceneService = Depends(get_scene_service),
):
    """Update editable fields of a scene (prompt, title, duration)."""
    result = await service.update_scene(
        scene_id=scene_id,
        user_id=ctx.user_id,
        title=body.title,
        prompt=body.prompt,
        duration=body.duration,
    )
    return success_response(result, "Scene updated")


@router.delete("/scenes/{scene_id}", response_model=BaseResponse)
async def delete_scene(
    scene_id: str,
    ctx: UserContext = Depends(get_user_context_or_default),
    service: SceneService = Depends(get_scene_service),
):
    """Remove a scene from its project."""
    await service.delete_scene(scene_id, user_id=ctx.user_id)
    return success_response(None, "Scene deleted")
