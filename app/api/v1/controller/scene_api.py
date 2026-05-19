"""Scene API controller — scenes + variations + NL instructions endpoints."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.tags import Tags
from app.api.v1.request.instruct_request import InstructSceneRequest
from app.api.v1.request.scene_request import (
    CreateSceneRequest,
    GenerateVariationsRequest,
    SelectVariationRequest,
    UpdateSceneRequest,
)
from app.api.v1.response.base_response import BaseResponse, success_response
from app.api.v1.response.job_response import JobResponse
from app.api.v1.response.scene_instruction_response import SceneInstructionResponse
from app.api.v1.response.scene_response import SceneResponse
from app.api.v1.response.variation_response import VariationResponse
from app.db.session import get_db
from app.service.instruct_service import InstructService
from app.service.scene_service import SceneService
from app.service.variation_service import VariationService

router = APIRouter(tags=[Tags.Scene])


def get_scene_service(db: AsyncSession = Depends(get_db)) -> SceneService:
    return SceneService(db)


def get_variation_service(db: AsyncSession = Depends(get_db)) -> VariationService:
    return VariationService(db)


def get_instruct_service(db: AsyncSession = Depends(get_db)) -> InstructService:
    return InstructService(db)


@router.post(
    "/projects/{project_id}/scenes",
    response_model=BaseResponse[SceneResponse],
    status_code=201,
)
async def add_scene(
    project_id: str,
    body: CreateSceneRequest,
    service: SceneService = Depends(get_scene_service),
):
    """Add a scene to a project."""
    result = await service.add_scene(
        project_id=project_id,
        template=body.template,
        title=body.title,
        prompt=body.prompt,
        params=body.params,
        duration=body.duration,
        style=body.style,
        motion=body.motion,
        n=body.n,
    )
    return success_response(result, "Scene added", 201)


@router.patch("/scenes/{scene_id}", response_model=BaseResponse[SceneResponse])
async def update_scene(
    scene_id: str,
    body: UpdateSceneRequest,
    force: bool = Query(
        default=False,
        description="Discard any extra_steps divergence when switching templates.",
    ),
    service: SceneService = Depends(get_scene_service),
):
    """Update prompt, template, params, duration, style.

    Switching templates is blocked if the scene has NL divergence (`extra_steps`).
    Pass `?force=true` to discard divergence and switch anyway.
    """
    result = await service.update_scene(
        scene_id=scene_id,
        title=body.title,
        template=body.template,
        prompt=body.prompt,
        params=body.params,
        duration=body.duration,
        style=body.style,
        motion=body.motion,
        force=force,
    )
    return success_response(result, "Scene updated")


@router.delete("/scenes/{scene_id}", response_model=BaseResponse)
async def delete_scene(
    scene_id: str,
    service: SceneService = Depends(get_scene_service),
):
    """Remove a scene from its project."""
    await service.delete_scene(scene_id)
    return success_response(None, "Scene deleted")


@router.post(
    "/scenes/{scene_id}/variations",
    response_model=BaseResponse[JobResponse],
    status_code=202,
)
async def generate_variations(
    scene_id: str,
    body: GenerateVariationsRequest,
    service: VariationService = Depends(get_variation_service),
):
    """Generate N variations for a scene. Returns a job to poll."""
    job = await service.generate_variations(scene_id, n=body.n, seed=body.seed)
    return success_response(job, "Variation generation queued", 202)


@router.get(
    "/scenes/{scene_id}/variations",
    response_model=BaseResponse[list[VariationResponse]],
)
async def list_variations(
    scene_id: str,
    service: VariationService = Depends(get_variation_service),
):
    """List all variations rendered for a scene."""
    result = await service.list_for_scene(scene_id)
    return success_response(result, "Variations fetched")


@router.patch(
    "/scenes/{scene_id}/select-variation",
    response_model=BaseResponse[SceneResponse],
)
async def select_variation(
    scene_id: str,
    body: SelectVariationRequest,
    service: SceneService = Depends(get_scene_service),
):
    """Pick which variation should be used when stitching."""
    result = await service.select_variation(scene_id, body.variation_id)
    return success_response(result, "Variation selected")


# ── NL scene editing ─────────────────────────────────────────────────────────
# Two-step by design: /instruct updates the scene's spec (sync, no render);
# user clicks render separately via POST /scenes/{id}/variations.


@router.post(
    "/scenes/{scene_id}/instruct",
    response_model=BaseResponse[SceneResponse],
)
async def instruct_scene(
    scene_id: str,
    body: InstructSceneRequest,
    service: InstructService = Depends(get_instruct_service),
):
    """Apply a natural-language edit to a scene.

    The planner (Claude) interprets the instruction against the scene's
    current template + params + extra_steps and produces a new `extra_steps`
    list. Synchronous — returns the updated SceneResponse. Does NOT trigger
    a re-render; call `POST /scenes/{id}/variations` separately when ready.
    """
    result = await service.instruct(scene_id, body.instruction)
    return success_response(result, "Instruction applied")


@router.get(
    "/scenes/{scene_id}/instructions",
    response_model=BaseResponse[list[SceneInstructionResponse]],
)
async def list_scene_instructions(
    scene_id: str,
    service: InstructService = Depends(get_instruct_service),
):
    """Audit trail: every NL instruction applied to this scene, in order."""
    rows = await service.list_instructions(scene_id)
    return success_response(
        [SceneInstructionResponse.model_validate(r) for r in rows],
        "Instructions fetched",
    )


@router.post(
    "/scenes/{scene_id}/collapse-instructions",
    response_model=BaseResponse[SceneResponse],
)
async def collapse_instructions(
    scene_id: str,
    service: InstructService = Depends(get_instruct_service),
):
    """Wipe instruction history; keep current `extra_steps` as the new baseline.

    Future instructions stack on top of this cleaned slate. The scene's visual
    state is unchanged.
    """
    result = await service.collapse(scene_id)
    return success_response(result, "Instruction history collapsed")


@router.post(
    "/scenes/{scene_id}/discard-divergence",
    response_model=BaseResponse[SceneResponse],
)
async def discard_divergence(
    scene_id: str,
    service: InstructService = Depends(get_instruct_service),
):
    """Drop all NL edits and revert to the pure template baseline."""
    result = await service.discard_divergence(scene_id)
    return success_response(result, "Divergence discarded")
